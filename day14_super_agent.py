"""
Day 14-3: SuperAgent - RAG + 工具的终极组合
🎯 让 Agent 自主决定：什么时候查知识库，什么时候用工具
"""
import os
import json
import requests
import chromadb
from datetime import datetime
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")


# ===== ChromaDB（沿用 Day 12）=====
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


# ===== 工具：把 RAG 包装成"知识库查询工具" =====
def search_knowledge_base(query: str, top_k: int = 3) -> list[dict]:
    """🔑 RAG 作为 Agent 的一个工具"""
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
            "description": "在私人知识库里搜索信息（关于用户的个人资料、公司文档等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
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


SYSTEM_PROMPT = """你是 SuperAgent，一个会思考的智能助手。

可用工具：
- search_knowledge_base: 查询私人知识库（用户个人信息、文档等）
- get_current_time: 获取当前时间  
- get_weather: 查询城市天气

工作原则：
1. 先在 content 里写"💭 思考"
2. 涉及"我/用户/我的..."的问题，**主动查知识库**
3. 涉及实时信息，调用对应工具
4. 综合所有信息后，用"✅ 答案"给出回复
"""


def call_llm(messages):
    r = requests.post(
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
    r.raise_for_status()
    return r.json()


def super_agent(question: str, max_steps: int = 6):
    print(f"\n💬 用户：{question}")
    print("=" * 60)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    for step in range(max_steps):
        msg = call_llm(messages)["choices"][0]["message"]
        
        if msg.get("content"):
            print(f"\n【Step {step+1}】{msg['content']}")
        
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            print("=" * 60)
            return msg.get("content", "")
        
        messages.append(msg)
        
        for tc in tool_calls:
            fn = tc["function"]["name"]
            args = json.loads(tc["function"]["arguments"])
            print(f"   🔧 {fn}({args})")
            
            result = available_tools[fn](**args) if fn in available_tools else f"未知 {fn}"
            print(f"   📊 {str(result)[:100]}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False)[:500],
            })


if __name__ == "__main__":
    # ⭐ 终极测试：Agent 自主组合 RAG + 工具
    test_cases = [
        "我的学习计划是什么？",                      # 只需要 RAG
        "现在几点了？",                              # 只需要工具
        "我现在该不该开始学习？",                    # ⭐ RAG（查学习时间）+ 工具（查当前时间）+ 推理
    ]
    
    for q in test_cases:
        super_agent(q)
        print("\n" + "🔚" * 30 + "\n")