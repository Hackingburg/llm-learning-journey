"""
Day 8-3: DeepChat 持久化版
🎯 服务重启数据不丢失， 多进程也能共享会话
"""

import os 
import json 
import uuid
import requests 
from datetime import datetime
from pathlib import Path
from typing import Literal 
from fastapi import FastAPI, HTTPException, Depends 
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, select, func 
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")


# ===== 数据库配置 ===== 
DB_PATH = Path("data/deepchat_sessions.db")
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ===== 数据库表 =====
class ChatSession(Base):
    """会话表：一个 session 一行"""
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True) # session_id (UUID)
    history_json = Column(String, default="[]")  # 历史消息存 JSON 字符串
    turn_count = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# 自动建表
Base.metadata.create_all(engine)

# ===== FastAPI =====
app = FastAPI(
    title="DeepChat with DB", version="2.0.0"
)

# ===== 数据模型 =====
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str 

class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None)
    message: str = Field(min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    session_id: str
    reply: str 
    turn_count: int 
    total_cost: float

class SessionInfo(BaseModel):
    session_id: str
    turn_count: int
    total_cost: float
    history: list[Message]
    created_at: datetime
    updated_at: datetime


# ===== 依赖注入：每个请求拿一个数据库 session =====
def get_db():
    """🔑 FastAPI 的依赖注入，自动管理数据库连接"""
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()


# ===== 配置 =====
SYSTEM_PROMPT = "你是一个简洁有趣的 AI 助手，回答控制在 150 字内"
MAX_HISTORY_TURNS = 10  # 滑动窗口


def call_llm(messages: list[dict]) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
        },
        timeout=30

    )
    response.raise_for_status()
    return response.json()


# ===== API 端点 ===== 
@app.get("/")
def root(db: Session = Depends(get_db)):
    count = db.execute(select(func.count(ChatSession.id))).scalar()
    return {"service": "DeepChat DB", "total_sessions": count}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """发消息（数据持久化版本）"""
    # 1. 获取或新建会话
    session = None
    if request.session_id:
        session = db.execute(select(ChatSession).where(ChatSession.id == request.session_id)).scalar_one_or_none()
    
    if session is None:
        session = ChatSession(id=str(uuid.uuid4()))
        db.add(session)
        db.flush() # 拿到 id， 但还没 commit

    # 2. 反序列化历史
    history = json.loads(session.history_json)
    history.append({"role": "user", "content": request.message})

    # 滑动窗口
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(history) > max_msgs:
        history = history[-max_msgs:]

    # 拼装 messages 
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    try: 
        data = call_llm(messages)
        reply = data["choices"][0]["message"]["content"]
        usage = data["usage"]

        cost = (usage["prompt_tokens"] / 1_000_000 * 2.0 + usage["completion_tokens"] / 1_000_000 * 8.0)  
        
        # 4. 更新会话状态
        history.append({"role": "assistant", "content": reply})
        session.history_json = json.dumps(history, ensure_ascii=False)
        session.turn_count += 1
        session.total_cost += cost

        db.commit()  # 🔑 提交事务，保存到数据库
        
        return ChatResponse(
            session_id=session.id,
            reply=reply,
            turn_count=session.turn_count,
            total_cost=round(session.total_cost, 6)
        )
    except Exception as e:
        # 回滚刚加的用户消息
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/sessions/{session_id}", response_model=SessionInfo)
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.execute(select(ChatSession).where(ChatSession.id == session_id)).scalar_one_or_none()


    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    history = json.loads(session.history_json)
    return SessionInfo(
        session_id=session.id,
        turn_count=session.turn_count,
        total_cost=round(session.total_cost, 6),
        history=[Message(**msg) for msg in history],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """删除会话"""
    session = db.execute(select(ChatSession).where(ChatSession.id == session_id)).scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    db.delete(session)
    db.commit()
    return {"detail": f"会话已删除 {session_id}"}

@app.get("/sessions")
def list_sessions(db: Session = Depends(get_db)):
    """列出所有活跃会话"""
    sessions = db.execute( select(ChatSession).order_by(ChatSession.updated_at.desc())).scalars().all()
    
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": session.id,
                "turn_count": session.turn_count,
                "total_cost": round(session.total_cost, 6),
                "updated_at": session.updated_at,
            } 
            for session in sessions   
        ]
    }