"""
Day 16: DeepChat Pro - 终极 Agent 产品 
🎯 流式 Agent + 多轮对话 + 持久化 + 美化 UI 
"""
import os
import json
import uuid 
import requests
import chromadb
import anyio 
from pathlib import Path 
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, select
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi import FastAPI, HTTPException 
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")


# ===== 配置 =====
DB_PATH = Path("data/deepchat_pro.db")
CHROMA_PATH = Path("data/chroma_rag")
DB_PATH.parent.mkdir(exist_ok=True) 
MAX_HISTORY_TURNS = 10


# ===== SQLAlchemy 会话持久化 =====
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(String, primary_key=True)
    title = Column(String, default="新对话")
    history_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


Base.metadata.create_all(engine)


# ===== ChromaDB =====
class SiliconFlowEmbedding(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            r = requests.post(
                "https://api.siliconflow.cn/v1/embeddings",
                headers={"Authorization": f"Bearer {SF_API_KEY}"},
                json={"model": "BAAI/bge-m3", "input": text},
                timeout=30
            )
            r.raise_for_status()
            embeddings.append(r.json()["data"][0]["embedding"])
        return embeddings


chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
kb = chroma_client.get_or_create_collection(
    name="knowledge_base",
    embedding_function=SiliconFlowEmbedding(),
)


# ===== 工具 =====
def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    results = kb.query(query_texts=[query], n_results=top_k)
    if not results["documents"][0]:
        return [{"info": "知识库为空"}]
    return [
        {"content": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


def get_current_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_weather(city: str) -> dict:
    fake_db = {
        "北京": {"温度": 5, "天气": "晴"},
        "上海": {"温度": 10, "天气": "多云"},
    }
    return fake_db.get(city, {"error": f"没有 {city} 的数据"})


available_tools = {
    "search_knowledge_base": search_knowledge_base,
    "get_current_time": get_current_time,
    "get_weather": get_weather,
}

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "搜索私人知识库",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前时间",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
]

SYSTEM_PROMPT = """你是 DeepChat Pro， 一个会思考的智能助手。

工作流程：
1. 先用一句话写下思考（如"我需要查...才能回答"）
2. 调用合适的工具
3. 得到结果后再思考下一步
4. 综合所有信息后给出最终回答

原则：
- 涉及"我/用户"的问题主动查知识库
- 涉及实时数据的问题主动调用工具
- 多轮对话时要记得上下文
- 不要编造数据"""


# ===== 流式 Agent 核心 =====
def sse_event(event_type: str, data: dict) -> str:
    """🔑 SSE 标准格式：event: xxx \n data: json \n\n"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def call_llm(messages: list) -> dict:
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat", 
            "messages": messages, 
            "tools": tools_schema, 
            "tool_choice": "auto", 
            "temperature": 0.3},
        timeout=60
    )
    response.raise_for_status()
    return response.json()


def stream_agent(question: str, history: list, max_steps: int = 6):
    """⭐ 流式 Agent 生成器：边思考边推送给前端"""
    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        +history
        + [{"role": "user", "content": question}] 
    )

    yield sse_event("start", {"question": question})
    
    # 收集本轮新产生的消息（用来更新 history）
    new_messages = [{"role": "user", "content": question}]
    final_answer = ""
    
    for step in range(max_steps):
        try:
            data = call_llm(messages)
        except Exception as e:
            yield sse_event("error", {"message": f"调用 LLM 失败: {e}"})
            return
        
        msg = data["choices"][0]["message"]
       
        if msg.get("content"):
            yield sse_event("thinking", {
                "step": step + 1,
                "content": msg["content"]
            })
        
        tool_calls = msg.get("tool_calls")
        
        # 没有工具调用 = 最终答案
        if not tool_calls:
            final_answer = msg.get("content", "")
            new_messages.append({"role": "assistant", "content": final_answer}) 
            yield sse_event("answer", {"content": final_answer})
            yield sse_event("done", {"total_steps": step + 1, "new_messsages": new_messages})
            return
        
        messages.append(msg)
        new_messages.append(msg)
        # 2. 推送工具调用 + 执行结果
        for tc in tool_calls:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            
            yield sse_event("tool_call", {"name": fn, "args": args})
            
            try:
                result = available_tools[fn](**args) if fn in available_tools else f"未知 {fn}"
            except Exception as e:
                result = f"工具执行失败: {e}"

            result_str = json.dumps(result, ensure_ascii=False)
            if len(result_str) > 500:
                result_str = result_str[:500] + " ...（结果过长被截断）"
            
            yield sse_event("tool_result", {
                "name": fn,
                "result": result_str[:200],  # 截断防爆
            })
            
            tool_msg = {
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_str,
            }
            messages.append(tool_msg)
            new_messages.append(tool_msg) 
    
    yield sse_event("done", {"reason": "达到最大步数"})


# ===== FastAPI =====
app = FastAPI(title="DeepChat Pro")


class AgentRequest(BaseModel):
    session_id: str | None = None
    message: str


@app.post("/agent/stream")
async def agent_stream(req: AgentRequest):
    """异步包装：避免阻塞 event loop"""
    db = SessionLocal()
    try:
        session = None
        if req.session_id:
            session = db.execute(
                select(AgentSession).where(AgentSession.id == req.session_id)
            ).scalar_one_or_none()
        
        if session is None:
            session = AgentSession(
                id=str(uuid.uuid4()),
                title=req.message[:30],
                history_json="[]"
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        session_id = session.id
        history = json.loads(session.history_json)
        
        # 滑动窗口：只保留最近 N 轮
        if len(history) > MAX_HISTORY_TURNS * 2:
            history = history[-MAX_HISTORY_TURNS * 2:]
    finally:
        db.close()
    
    # 2. 流式生成
    async def async_gen():
        # 先把 session_id 推给前端
        yield sse_event("session", {"session_id": session_id})
        
        gen = stream_agent(req.message, history)
        all_new_messages = []
        
        while True:
            event = await anyio.to_thread.run_sync(next, gen, None)
            if event is None:
                break
            
            # 🔑 拦截 done 事件，提取新消息用于持久化
            if 'event: done' in event:
                try:
                    data_line = [l for l in event.split('\n') if l.startswith('data: ')][0]
                    done_data = json.loads(data_line[6:])
                    all_new_messages = done_data.get("new_messages", [])
                except Exception:
                    pass
            
            yield event
        
        # 3. 流结束后，持久化新消息
        if all_new_messages:
            db = SessionLocal()
            try:
                session = db.execute(
                    select(AgentSession).where(AgentSession.id == session_id)
                ).scalar_one_or_none()
                if session:
                    full_history = json.loads(session.history_json) + all_new_messages
                    session.history_json = json.dumps(full_history, ensure_ascii=False)
                    db.commit()
            finally:
                db.close()
    
    return StreamingResponse(async_gen(), media_type="text/event-stream")



# ===== 自带前端 UI =====
@app.get("/sessions")
def list_sessions():
    """列出所有对话"""
    db = SessionLocal()
    try:
        sessions = db.execute(
            select(AgentSession).order_by(AgentSession.updated_at.desc())
        ).scalars().all()
        return [
            {
                "id": s.id,
                "title": s.title,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in sessions
        ]
    finally:
        db.close()


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """获取某个对话的完整历史（用于前端展示）"""
    db = SessionLocal()
    try:
        session = db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        ).scalar_one_or_none()
        if not session:
            raise HTTPException(404, "会话不存在")
        
        history = json.loads(session.history_json)
        # 只返回 user / assistant 消息，过滤掉 tool 内部消息
        visible = [
            {"role": m["role"], "content": m.get("content", "")}
            for m in history
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        return {"id": session.id, "title": session.title, "messages": visible}
    finally:
        db.close()


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    db = SessionLocal()
    try:
        session = db.execute(
            select(AgentSession).where(AgentSession.id == session_id)
        ).scalar_one_or_none()
        if session:
            db.delete(session)
            db.commit()
        return {"ok": True}
    finally:
        db.close()


# ===== 美化前端 =====
@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_HTML




FRONTEND_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>DeepChat Pro 🧠</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", sans-serif; height: 100vh; display: flex; background: #f7f7f8; }

/* 左侧对话列表 */
.sidebar { width: 240px; background: #202123; color: #fff; padding: 15px; overflow-y: auto; }
.sidebar h2 { font-size: 16px; margin-bottom: 15px; }
.new-chat { width: 100%; padding: 10px; background: transparent; color: #fff; border: 1px solid #555; border-radius: 6px; cursor: pointer; margin-bottom: 15px; }
.new-chat:hover { background: #2a2b32; }
.session-item { padding: 10px; cursor: pointer; border-radius: 6px; font-size: 13px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.session-item:hover { background: #2a2b32; }
.session-item.active { background: #343541; }

/* 主区域 */
.main { flex: 1; display: flex; flex-direction: column; }
.header { padding: 15px 20px; background: #fff; border-bottom: 1px solid #e5e5e5; font-weight: 600; }
.messages { flex: 1; overflow-y: auto; padding: 20px; }
.msg { max-width: 800px; margin: 0 auto 20px; padding: 16px 20px; border-radius: 12px; line-height: 1.6; }
.msg.user { background: #e7f3ff; align-self: flex-end; }
.msg.assistant { background: #fff; border: 1px solid #e5e5e5; }
.msg .role { font-size: 12px; color: #888; margin-bottom: 6px; }
.msg .thinking { color: #888; font-style: italic; font-size: 13px; padding: 4px 0; }
.msg .tool { color: #2563eb; font-family: monospace; font-size: 13px; padding: 2px 0; }
.msg .result { color: #16a34a; font-family: monospace; font-size: 12px; padding: 2px 0; }

/* 输入区 */
.input-area { padding: 16px 20px; background: #fff; border-top: 1px solid #e5e5e5; }
.input-wrap { max-width: 800px; margin: 0 auto; display: flex; gap: 10px; }
#input { flex: 1; padding: 12px; font-size: 15px; border: 1px solid #ccc; border-radius: 8px; outline: none; }
#input:focus { border-color: #2563eb; }
#send { padding: 12px 24px; background: #10a37f; color: #fff; border: none; border-radius: 8px; font-size: 15px; cursor: pointer; }
#send:disabled { background: #aaa; cursor: not-allowed; }
#send:hover:not(:disabled) { background: #0e8d6c; }
</style>
</head>
<body>

<div class="sidebar">
    <button class="new-chat" onclick="newChat()">+ 新对话</button>
    <h2>历史对话</h2>
    <div id="sessions"></div>
</div>

<div class="main">
    <div class="header">DeepChat Pro 🧠 — 你的私人 AI Agent</div>
    <div class="messages" id="messages"></div>
    <div class="input-area">
        <div class="input-wrap">
            <input id="input" placeholder="问我点什么..." onkeydown="if(event.key==='Enter')send()" />
            <button id="send" onclick="send()">发送</button>
        </div>
    </div>
</div>

<script>
let currentSessionId = null;

async function loadSessions() {
    const res = await fetch("/sessions");
    const sessions = await res.json();
    const div = document.getElementById("sessions");
    div.innerHTML = "";
    sessions.forEach(s => {
        const item = document.createElement("div");
        item.className = "session-item" + (s.id === currentSessionId ? " active" : "");
        item.textContent = s.title;
        item.onclick = () => loadSession(s.id);
        div.appendChild(item);
    });
}

async function loadSession(id) {
    currentSessionId = id;
    const res = await fetch("/sessions/" + id);
    const data = await res.json();
    const box = document.getElementById("messages");
    box.innerHTML = "";
    data.messages.forEach(m => {
        addMsg(m.role, m.content);
    });
    loadSessions();
}

function newChat() {
    currentSessionId = null;
    document.getElementById("messages").innerHTML = "";
    loadSessions();
}

function addMsg(role, content) {
    const box = document.getElementById("messages");
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = `<div class="role">${role === 'user' ? '🧑 你' : '🤖 AI'}</div><div class="content">${content}</div>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    return div;
}

function appendDetail(msgDiv, className, text) {
    const d = document.createElement("div");
    d.className = className;
    d.textContent = text;
    msgDiv.querySelector(".content").appendChild(d);
    document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
}

async function send() {
    const input = document.getElementById("input");
    const btn = document.getElementById("send");
    const text = input.value.trim();
    if (!text) return;
    
    btn.disabled = true;
    input.value = "";
    
    addMsg("user", text);
    const aiMsg = addMsg("assistant", "");
    aiMsg.querySelector(".content").innerHTML = "";
    
    try {
        const res = await fetch("/agent/stream", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({session_id: currentSessionId, message: text}),
        });
        
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const events = buffer.split("\\n\\n");
            buffer = events.pop();
            
            for (const evt of events) {
                const lines = evt.split("\\n");
                let eventType = "", data = "";
                for (const line of lines) {
                    if (line.startsWith("event: ")) eventType = line.slice(7);
                    if (line.startsWith("data: ")) data = line.slice(6);
                }
                if (!eventType) continue;
                const obj = JSON.parse(data);
                
                if (eventType === "session") currentSessionId = obj.session_id;
                else if (eventType === "thinking") appendDetail(aiMsg, "thinking", "💭 " + obj.content);
                else if (eventType === "tool_call") appendDetail(aiMsg, "tool", "🔧 " + obj.name + "(" + JSON.stringify(obj.args) + ")");
                else if (eventType === "tool_result") appendDetail(aiMsg, "result", "📊 " + obj.result);
                else if (eventType === "answer") {
                    const ans = document.createElement("div");
                    ans.style.marginTop = "10px";
                    ans.style.fontWeight = "500";
                    ans.textContent = obj.content;
                    aiMsg.querySelector(".content").appendChild(ans);
                }
            }
        }
    } catch (e) {
        appendDetail(aiMsg, "thinking", "❌ 错误: " + e.message);
    } finally {
        btn.disabled = false;
        input.focus();
        loadSessions();
    }
}

loadSessions();
</script>
</body>
</html>
"""


# 启动：uvicorn day16_deepchat_pro:app --reload