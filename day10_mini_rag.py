"""
Day 10-3: 最小可用 RAG 系统
🎯 让 AI 基于你的私人文档回答问题

完整流程：
1. 读文档 → 2. 分块 → 3. 每块算 Embedding → 
4. 用户提问 → 5. 算问题 Embedding → 6. 找最相似的 3 块 → 
7. 塞给 LLM 一起回答
"""
import os
import requests
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 工具函数 =====
def get_embedding(text: str) -> list[float]:
    """获取文本 embedding"""
    response = requests.post(
        "https://api.siliconflow.cn/v1/embeddings",
        headers={"Authorization": f"Bearer {SF_API_KEY}"},
        json={"model": "BAAI/bge-m3", "input": text},
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """余弦相似度"""
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def chunk_by_paragraph(text: str) -> list[str]:
    """按段落分块"""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


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


# ===== RAG 核心类 =====
class MiniRAG:
    """最小可用 RAG 系统"""
    
    def __init__(self, doc_path: str):
        self.doc_path = Path(doc_path)
        self.chunks: list[str] = []
        self.embeddings: list[list[float]] = []
    
    def build_index(self):
        """
        🔑 第一步：把文档变成可检索的"向量库"
        这一步只做一次（实际生产会存到向量数据库里）
        """
        print(f"📖 读取文档：{self.doc_path}")
        text = self.doc_path.read_text(encoding="utf-8")
        
        print("✂️ 分块...")
        self.chunks = chunk_by_paragraph(text)
        print(f"   切成了 {len(self.chunks)} 块")
        
        print("🧮 计算 embeddings（每块都要调一次 API）...")
        self.embeddings = []
        for i, chunk in enumerate(self.chunks, 1):
            emb = get_embedding(chunk)
            self.embeddings.append(emb)
            print(f"   ✅ 块 {i}/{len(self.chunks)} 完成")
        
        print(f"\n✅ 索引构建完成！\n")
    
    def retrieve(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """
        🔑 第二步：根据问题找最相关的几块
        返回：[(块内容, 相似度), ...]
        """
        query_emb = get_embedding(query)
        
        scored = []
        for chunk, emb in zip(self.chunks, self.embeddings):
            sim = cosine_similarity(query_emb, emb)
            scored.append((chunk, sim))
        
        # 按相似度降序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
    
    def ask(self, query: str, top_k: int = 3, show_context: bool = True) -> str:
        """
        🔑 第三步：检索 + 生成（RAG 完整流程）
        """
        print(f"\n❓ 问题：{query}\n")
        
        # 1. 检索
        retrieved = self.retrieve(query, top_k=top_k)
        
        if show_context:
            print("📚 找到的相关内容：")
            for i, (chunk, sim) in enumerate(retrieved, 1):
                print(f"  [{i}] 相似度={sim:.3f}")
                print(f"      {chunk[:80]}{'...' if len(chunk) > 80 else ''}")
            print()
        
        # 2. 构造 prompt（把检索结果塞进 system prompt）
        context = "\n\n".join([f"【片段{i+1}】{chunk}" for i, (chunk, _) in enumerate(retrieved)])
        
        system_prompt = f"""你是一个基于私人知识库的 AI 助手。
请仅根据以下"参考资料"回答用户的问题。
如果参考资料里没有相关信息，请直接说"我在知识库里没找到相关信息"，不要编造。

参考资料：
{context}"""
        
        # 3. 生成
        reply = call_llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ])
        
        print(f"🤖 回答：{reply}\n")
        return reply


# ===== 实战测试 =====
if __name__ == "__main__":
    rag = MiniRAG("data/my_docs.txt")
    rag.build_index()
    
    print("=" * 60)
    print("🧪 测试 RAG：问 AI 关于'王兴'的问题")
    print("=" * 60)
    
    # 这些问题的答案都在 my_docs.txt 里
    test_questions = [
        "王兴的学习计划是什么？",
        "他喜欢喝什么咖啡？",
        "他的 DeepChat 部署在哪里？",
        "他周末做什么？",
        # 反例：知识库里没有的
        "王兴的银行卡号是多少？",
    ]
    
    for q in test_questions:
        rag.ask(q)
        print("-" * 60)