"""
Day 7-3: DeepChat Web 服务化
🎯 Day 4 的多轮对话变成 Web API，支持多用户并发
"""

import os 
import uuid
import requests 
from typing import Literal 
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")

app = FastAPI(
    title="DeepChat Web API", version="1.0.0"
)

# ===== 数据模型 =====
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str 

class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="会话 ID，不传则新建")
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


# ===== 会话存储（简化版：内存字典） =====
# 🔑 生产环境会用 Redis / 数据库，今天先用字典理解原理
sessions: dict[str, dict] = {}

SYSTEM_PROMPT = "你是一个简洁有趣的 AI 助手，回答控制在 150 字内"
MAX_HISTORY_TURNS = 10  # 滑动窗口

def get_or_create_session(session_id: str | None) -> tuple[str, dict]:
    """获取已有会话，或新建一个"""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    
    # 新建会话
    new_id = session_id or str(uuid.uuid4())
    sessions[new_id] = {
        "history": [],
        "total_cost": 0.0,
        "turn_count":0,
    }
    return new_id, sessions[new_id]

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
def root():
    return {"service": "DeepChat API", "active_sessions":len(sessions)}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """发消息（自动维护会话历史）"""
    sid, session = get_or_create_session(request.session_id)

    # 加入用户消息 
    session["history"].append(Message(role="user", content=request.message))

    # 滑动窗口
    max_msgs = MAX_HISTORY_TURNS * 2
    if len(session["history"]) > max_msgs:
        session["history"] = session["history"][-max_msgs:]

    # 拼装 messages 
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": msg.role, "content": msg.content} for msg in session["history"]]  

    try: 
        data = call_llm(messages)
        reply = data["choices"][0]["message"]["content"]
        usage = data["usage"]

        # 累计成本计算
        cost = (usage["prompt_tokens"] / 1_000_000 * 2.0 + usage["completion_tokens"] / 1_000_000 * 8.0)  
        session["total_cost"] += cost
        session["turn_count"] += 1

        # 加入助手回复
        session["history"].append(Message(role="assistant", content=reply))
        
        return ChatResponse(
            session_id=sid,
            reply=reply,
            turn_count=session["turn_count"],
            total_cost=session["total_cost"] 
        )
    except Exception as e:
        # 回滚刚加的用户消息
        session["history"].pop()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/sessions/{session_id}", response_model=SessionInfo)
def get_session(session_id: str):
    """查询会话详情"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        turn_count=session["turn_count"],
        total_cost=session["total_cost"],
        history=session["history"]
    )

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """删除会话"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    del sessions[session_id]
    return {"detail": f"会话已删除 {session_id}"}

@app.get("/sessions")
def list_sessions():
    """列出所有活跃会话"""
    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "turn_count": session["turn_count"],
                "total_cost": session["total_cost"]
            } for sid, session in sessions.items()
        ]
    }