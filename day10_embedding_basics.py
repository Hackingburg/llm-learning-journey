"""
Day 10-1: Embedding 入门 - 感受"语义距离"
目标：理解为什么"我爱吃苹果"和"我喜欢吃水果"的向量很像
"""
import os 
import requests 
import numpy as np
from dotenv import load_dotenv

load_dotenv()
SF_API_KEY = os.getenv("SILICONFLOW_API_KEY")

if not SF_API_KEY:
    raise ValueError("❌ 没找到 SILICONFLOW_API_KEY")


def get_embedding(text: str) -> list[float]:
    """
    🔑 把文本变成向量
    用硅基流动的 BAAI/bge-m3 模型（中文 embedding 神器，1024 维）
    """

    response = requests.post(
        "https://api.siliconflow.cn/v1/embeddings",
        headers={
            "Authorization": f"Bearer {SF_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "BAAI/bge-m3",
            "input": text,
        },
        timeout=30
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    🔑 余弦相似度：衡量两个向量有多"像"
    返回值范围 [-1，1], 越接近 1 越像
    """
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def main():
    # ===== 实验 1: 单个向量长什么样呢 =====
    print("=" * 60)
    print("🧪 实验 1：看看向量长啥样")
    print("=" * 60)

    vec = get_embedding("我爱吃苹果")
    print(f"向量维度：{len(vec)}")
    print(f"向量前 10 个数：{vec[:10]}")
    print(f"💡 这就是一段文字的'数学指纹'")

    # ===== 实验 2: 语义距离对比 =====
    print("\n" + "=" * 60)
    print("🧪 实验 2：语义相似度对比")
    print("=" * 60)

    query = "我爱吃苹果"
    candidates = [
        "我喜欢吃水果",
        "苹果手机很贵",
        "今天天气真好",
        "I love eating apples",
    ]

    query_vec = get_embedding(query)
    print(f"\n 基准句子： '{query}'\n")

    results = []
    for text in candidates:
        text_vec = get_embedding(text)
        sim =cosine_similarity(query_vec, text_vec)
        results.append((text, sim))

    # 按相似度排序
    results.sort(key=lambda x: x[1], reverse=True)

    print("相似度排名(从高到低)：")
    for text, sim in results:
        bar = "█" * int(sim * 30)
        print(f"  {sim:.3f} {bar} {text}")  

    print("\n💡 关键观察：")
    print("  - '我喜欢吃水果' 应该最高，因为它和基准句子意思最接近")
    print("  - '苹果手机很贵' 可能次之，因为它提到了'苹果'这个词")
    print("  - 'I love eating apples' 可能也很高，因为它是英文版的基准句子")
    print("  ➡️ 这就是为什么 Embedding 比关键词搜索强 100 倍")

if __name__ == "__main__":
    main()
