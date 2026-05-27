"""
Day 15-3: 流式 Agent Web 服务
🎯 浏览器实时看到 Agent 的思考、工具调用、最终答案
"""
import os
import json
import requests
import chromadb
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")


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


chroma_client = chromadb.PersistentClient(path="data/chroma_rag")
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

SYSTEM_PROMPT = """你是 SuperAgent。
工作流程：
1. 先用一句话写下思考（如"我需要查...才能回答"）
2. 调用合适的工具
3. 得到结果后再思考下一步
4. 综合所有信息后给出最终回答

⚠️ 涉及"我/用户"的问题主动查知识库
⚠️ 不要编造数据"""


# ===== 流式 Agent 核心 =====
def sse_event(event_type: str, data: dict) -> str:
    """🔑 SSE 标准格式：event: xxx \n data: json \n\n"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def stream_agent(question: str, max_steps: int = 6):
    """⭐ 流式 Agent 生成器：边思考边推送给前端"""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    # 推送"开始"事件
    yield sse_event("start", {"question": question})
    
    for step in range(max_steps):
        # ⚠️ 注意：tools + stream=True 时不能用流式拿 content
        # 因为 DeepSeek 要先决定要不要调工具，所以这一步用非流式
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "tools": tools_schema,
                "tool_choice": "auto",
                "temperature": 0.3,
            },
            timeout=30
        )
        msg = response.json()["choices"][0]["message"]
        
        # 1. 推送 AI 的思考
        if msg.get("content"):
            yield sse_event("thinking", {
                "step": step + 1,
                "content": msg["content"]
            })
        
        tool_calls = msg.get("tool_calls")
        
        # 没有工具调用 = 最终答案
        if not tool_calls:
            yield sse_event("answer", {"content": msg.get("content", "")})
            yield sse_event("done", {"total_steps": step + 1})
            return
        
        messages.append(msg)
        
        # 2. 推送工具调用 + 执行结果
        for tc in tool_calls:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            
            yield sse_event("tool_call", {"name": fn, "args": args})
            
            try:
                result = available_tools[fn](**args) if fn in available_tools else f"未知 {fn}"
            except Exception as e:
                result = f"工具执行失败: {e}"
            
            yield sse_event("tool_result", {
                "name": fn,
                "result": str(result)[:200],  # 截断防爆
            })
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False)[:500],
            })
    
    yield sse_event("done", {"reason": "达到最大步数"})


# ===== FastAPI =====
app = FastAPI(title="Streaming Agent")


class AgentRequest(BaseModel):
    message: str


@app.post("/agent/stream")
def agent_stream(req: AgentRequest):
    """⭐ 流式 Agent API"""
    return StreamingResponse(
        stream_agent(req.message),
        media_type="text/event-stream"
    )


# ===== 自带前端 UI =====
@app.get("/", response_class=HTMLResponse)
def index():
    """简易 UI：让你能立刻在浏览器测试"""
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SuperAgent 流式版</title>
<style>
body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 30px auto; padding: 20px; }
h1 { color: #333; }
#input { width: 70%; padding: 10px; font-size: 16px; }
#send { padding: 10px 20px; font-size: 16px; cursor: pointer; }
#output { margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; min-height: 200px; white-space: pre-wrap; font-family: monospace; }
.thinking { color: #888; font-style: italic; }
.tool { color: #2563eb; }
.result { color: #16a34a; }
.answer { color: #000; font-weight: bold; font-size: 16px; }
.done { color: #9333ea; }
</style>
</head>
<body>
<h1>🧠 SuperAgent 流式版</h1>
<input id="input" placeholder="问我点什么..." value="我现在该做什么？" />
<button id="send">发送</button>
<div id="output"></div>

<script>
document.getElementById("send").onclick = async () => {
    const input = document.getElementById("input").value;
    const output = document.getElementById("output");
    output.innerHTML = "";
    
    const response = await fetch("/agent/stream", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: input}),
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, {stream: true});
        const events = buffer.split("\\n\\n");
        buffer = events.pop();  // 最后一段可能不完整
        
        for (const evt of events) {
            const lines = evt.split("\\n");
            let eventType = "", data = "";
            for (const line of lines) {
                if (line.startsWith("event: ")) eventType = line.slice(7);
                if (line.startsWith("data: ")) data = line.slice(6);
            }
            if (!eventType) continue;
            
            const obj = JSON.parse(data);
            const div = document.createElement("div");
            
            if (eventType === "start") div.textContent = "🚀 开始：" + obj.question;
            else if (eventType === "thinking") { div.className = "thinking"; div.textContent = "💭 " + obj.content; }
            else if (eventType === "tool_call") { div.className = "tool"; div.textContent = "🔧 调用 " + obj.name + "(" + JSON.stringify(obj.args) + ")"; }
            else if (eventType === "tool_result") { div.className = "result"; div.textContent = "📊 " + obj.result; }
            else if (eventType === "answer") { div.className = "answer"; div.textContent = "✅ " + obj.content; }
            else if (eventType === "done") { div.className = "done"; div.textContent = "🏁 完成"; }
            
            output.appendChild(div);
        }
    }
};
</script>
</body>
</html>
"""


# 启动：uvicorn day15_streaming_agent:app --reload