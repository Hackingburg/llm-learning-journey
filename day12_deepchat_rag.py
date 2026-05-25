"""
Day 12: DeepChat RAG - 集大成版
🎯 把 ChatBot + 数据库 + RAG 全部串起来
"""
import os
import json
import uuid
import requests
import chromadb
from datetime import datetime
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, select
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")


# ===== 配置 =====
DB_PATH = Path("data/deepchat_rag.db")
CHROMA_PATH = Path("data/chroma_rag")
DB_PATH.parent.mkdir(exist_ok=True)
SYSTEM_PROMPT_NO_RAG = "你是一个简洁有趣的 AI 助手，回答控制在 150 字内"
MAX_HISTORY_TURNS = 10


# ===== SQLAlchemy 会话持久化（沿用 Day 8）=====
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True)
    history_json = Column(String, default="[]")
    turn_count = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ===== ChromaDB 向量库（沿用 Day 11）=====
class SiliconFlowEmbedding(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            response = requests.post(
                "https://api.siliconflow.cn/v1/embeddings",
                headers={"Authorization": f"Bearer {SF_API_KEY}"},
                json={"model": "BAAI/bge-m3", "input": text},
                timeout=30
            )
            response.raise_for_status()
            embeddings.append(response.json()["data"][0]["embedding"])
        return embeddings


chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
kb_collection = chroma_client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=SiliconFlowEmbedding(),
)


# ===== LLM 调用 =====
def call_llm(messages: list[dict]) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={"model": "deepseek-chat", "messages": messages, "temperature": 0.3},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


# ===== FastAPI =====
app = FastAPI(title="DeepChat RAG", version="3.0.0")


# ===== Pydantic 模型 =====
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None)
    message: str = Field(min_length=1, max_length=2000)
    use_rag: bool = Field(default=False, description="是否启用 RAG")
    kb_filter: str | None = Field(default=None, description="只在某个文档里搜，如 'hr'")
    top_k: int = Field(default=3, ge=1, le=10)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    used_rag: bool
    retrieved_sources: list[str] = []
    turn_count: int
    total_cost: float


class UploadResponse(BaseModel):
    source: str
    chunks_added: int
    total_chunks_in_kb: int


# ===== 工具函数 =====
def chunk_text(text: str) -> list[str]:
    """按段落分块"""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def retrieve_context(query: str, top_k: int, kb_filter: str | None) -> tuple[str, list[str]]:
    """RAG 检索，返回 (上下文文本, 来源列表)"""
    where = {"source": kb_filter} if kb_filter else None
    
    results = kb_collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where,
    )
    
    if not results["documents"][0]:
        return "", []
    
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    
    context = "\n\n".join([f"【来源:{s}】{c}" for c, s in zip(chunks, sources)])
    return context, sources


def build_rag_system_prompt(context: str) -> str:
    """构造 RAG 模式的 system prompt"""
    return f"""你是基于私人知识库的 AI 助手。
请仅根据以下"参考资料"回答用户问题。
如果资料里没有相关内容，直接说"知识库里没找到相关信息"，绝对不要编造。

参考资料：
{context}"""


# ===== API 端点：知识库管理 =====
@app.post("/kb/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """⭐ 上传文档到知识库"""
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="只支持 .txt 和 .md 文件")
    
    try:
       content = (await file.read()).decode("utf-8")
    finally:
        await file.close()
    chunks = chunk_text(content)
    
    if not chunks:
        raise HTTPException(status_code=400, detail="文件内容为空")
    
    source = file.filename.replace(".txt", "").replace(".md", "")
    ids = [f"{source}#{i}" for i in range(len(chunks))]
    metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]
    
    # 用 upsert：同名文档重复上传 = 更新
    kb_collection.upsert(documents=chunks, ids=ids, metadatas=metadatas)
    
    return UploadResponse(
        source=source,
        chunks_added=len(chunks),
        total_chunks_in_kb=kb_collection.count(),
    )


@app.get("/kb/docs")
def list_documents():
    """查看知识库里的所有文档"""
    all_data = kb_collection.get()
    sources = set(m["source"] for m in all_data["metadatas"])
    
    stats = []
    for src in sources:
        count = sum(1 for m in all_data["metadatas"] if m["source"] == src)
        stats.append({"source": src, "chunks": count})
    
    return {"total_chunks": kb_collection.count(), "documents": stats}


@app.delete("/kb/docs/{source}")
def delete_document(source: str):
    """删除某个文档（按 source 过滤）"""
    all_data = kb_collection.get(where={"source": source})
    if not all_data["ids"]:
        raise HTTPException(status_code=404, detail=f"文档 {source} 不存在")
    
    kb_collection.delete(ids=all_data["ids"])
    return {"deleted_chunks": len(all_data["ids"]), "source": source}


# ===== API 端点：对话 =====
@app.get("/")
def root():
    return {
        "service": "DeepChat RAG",
        "kb_size": kb_collection.count(),
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """⭐ 智能对话（可选 RAG）"""
    # 1. 获取/创建会话
    session = None
    if request.session_id:
        session = db.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        ).scalar_one_or_none()
    
    if session is None:
        session = ChatSession(id=str(uuid.uuid4()))
        db.add(session)
        db.flush()
    
    # 2. 反序列化历史
    history = json.loads(session.history_json)
    history.append({"role": "user", "content": request.message})
    
    # 滑动窗口
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-MAX_HISTORY_TURNS * 2:]
    
    # 3. ⭐ RAG 分支：根据 use_rag 决定 system prompt
    retrieved_sources = []
    if request.use_rag:
        context, retrieved_sources = retrieve_context(
            query=request.message,
            top_k=request.top_k,
            kb_filter=request.kb_filter,
        )
        if context:
            system_prompt = build_rag_system_prompt(context)
        else:
            system_prompt = SYSTEM_PROMPT_NO_RAG  # 知识库为空时退化
    else:
        system_prompt = SYSTEM_PROMPT_NO_RAG
    
    # 4. 拼装 messages
    messages = [{"role": "system", "content": system_prompt}] + history
    
    try:
        data = call_llm(messages)
        reply = data["choices"][0]["message"]["content"]
        usage = data["usage"]
        
        cost = (usage["prompt_tokens"] / 1_000_000 * 2.0
                + usage["completion_tokens"] / 1_000_000 * 8.0)
        
        # 5. 更新会话
        history.append({"role": "assistant", "content": reply})
        session.history_json = json.dumps(history, ensure_ascii=False)
        session.turn_count += 1
        session.total_cost += cost
        db.commit()
        
        return ChatResponse(
            session_id=session.id,
            reply=reply,
            used_rag=request.use_rag and bool(retrieved_sources),
            retrieved_sources=list(set(retrieved_sources)),
            turn_count=session.turn_count,
            total_cost=round(session.total_cost, 6),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# 启动：uvicorn day12_deepchat_rag:app --reload