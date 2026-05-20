"""
Day 11-2: 用 ChromaDB 重构 RAG 
🎯 解决昨天的两大痛点：持久化 + 检索加速
"""

import os
import requests
import chromadb
from pathlib import Path
from chromadb.api.types import Documents, Embeddings, EmbeddingFunction
from dotenv import load_dotenv

load_dotenv()
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 自定义 Embedding 函数（用硅基流动 bge-m3 模型）=====
class SiliconFlowEmbedding(EmbeddingFunction):
    """🔑 让 ChromaDB 用我们制定的embedding 模型"""
    
    def __call__(self, input:Documents) -> Embeddings:
        # input 是一个文档列表，需要批量返回 embedding
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

def call_llm(messages: list[dict]) -> str:
    """调用 DeepSeek"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={"model": "deepseek-chat", "messages": messages, "temperature": 0.3},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ===== RAG 系统 =====
class ChromaRAG:
    """工业级 RAG 系统（V2）"""
    
    def __init__(self, db_path: str = "data/chroma_rag", collection_name: str = "my_docs"):
        # 1. 持久化客户端
        Path(db_path).parent.mkdir(exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)

        # 2. 创建集合 + 指定 embedding 函数
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=SiliconFlowEmbedding(),
        )

    def ingest(self, doc_path: str, source_name: str = None):
        """读文档 + 分块 + 入库（一次性操作）"""
        path = Path(doc_path)
        text = path.read_text(encoding="utf-8")
        source = source_name or path.name
        
        # 按段落分块
        chunks = [p.strip() for p in text.split("\n\n") if p.strip()]
        print(f"📖 {path.name}：切成 {len(chunks)} 块")
        
        # 🔑 用稳定的 id（含文件名），同样 id 会"更新"而不是"插入"
        ids = [f"{source}#{i}" for i in range(len(chunks))]
        metadatas = [{"source": source, "chunk_index": i} for i in range(len(chunks))]
        
        # 入库（embedding 自动计算 + 持久化）
        self.collection.upsert(
            documents=chunks,
            ids=ids,
            metadatas=metadatas,
        )
        print(f"✅ 已入库（集合总数：{self.collection.count()}）")
    
    def ask(self, query: str, top_k: int = 3, where: dict = None) -> str:
        """检索 + 生成"""
        print(f"\n❓ 问题：{query}")
        
        # 1. 检索
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,  # 可选过滤
        )
        
        chunks = results["documents"][0]
        distances = results["distances"][0]
        sources = [m["source"] for m in results["metadatas"][0]]
        
        # 2. 展示检索结果
        print("📚 找到的相关内容：")
        for i, (chunk, dist, src) in enumerate(zip(chunks, distances, sources), 1):
            print(f"  [{i}] 距离={dist:.3f} | 来源={src}")
            print(f"      {chunk[:80]}{'...' if len(chunk) > 80 else ''}")
        
        # 3. 构造 prompt
        context = "\n\n".join([f"【来源:{s}】{c}" for c, s in zip(chunks, sources)])
        system_prompt = f"""你是基于私人知识库的 AI 助手。
仅根据以下"参考资料"回答用户问题。
如果资料里没有，直接说"知识库里没找到相关信息"，不要编造。

参考资料：
{context}"""
        
        # 4. 调用 LLM
        reply = call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ])
        print(f"\n🤖 回答：{reply}\n")
        return reply


# ===== 实战测试 =====
if __name__ == "__main__":
    rag = ChromaRAG()
    
    # 入库（同一个文档第二次运行不会重复，因为用 upsert）
    rag.ingest("data/my_docs.txt")
    
    print("\n" + "=" * 60)
    print("🧪 测试 RAG（用 ChromaDB 加速版）")
    print("=" * 60)
    
    questions = [
        "王兴的学习计划是什么？",
        "他喜欢喝什么咖啡？",
        "他的项目部署在哪里？",
        "他的银行卡号是？",  # 反例
    ]
    
    for q in questions:
        rag.ask(q)
        print("-" * 60)
    
    print("\n💡 关键验证：")
    print("   1. 再运行一次这个程序，看看是不是不需要重算 embedding")
    print("   2. 重启后数据还在，因为持久化到了 data/chroma_rag/")