"""
Day 11-1: ChromaDB 入门
🎯 体验"3 行代码搞定向量数据库"
"""
import chromadb
from pathlib import Path

# ===== 1. 创建持久化客户端（数据存到磁盘）=====
DB_PATH = Path("data/chroma_db")
DB_PATH.parent.mkdir(exist_ok=True)

client = chromadb.PersistentClient(path=str(DB_PATH))
print(f"✅ Chrome DB 已就绪， 数据目录：{DB_PATH}")


# ===== 2. 创建/获取一个"集合"（类似 SQL 的表）=====
collection = client.get_or_create_collection(
    name="my_first_collection",
    metadata={"description": " Day 11 学习"}
)
print(f"✅ 集合已创建：{collection.name}")

# ===== 3. 插入文档（Chroma DB 自动算 embedding！）=====
# 注意：默认用 all-MiniLM-L6-v2 模型，中文效果一般，但今天先体验流程
collection.add(
    documents=[
        "我爱吃苹果",
        "我喜欢吃水果",
        "苹果手机很贵",
        "今天天气真好",
        "I love eating apples",
    ],
    ids=["1", "2", "3", "4", "5"],  # 🔑 每个文档要有唯一 id
    metadatas=[
        {"category": "food"},
        {"category": "food"},
        {"category": "tech"},
        {"category": "weather"},
        {"category": "food"},
    ]
)
print(f"✅ 已插入 5 条文档到集合 '{collection.name}'")


# ===== 4. 检索（神奇时刻!）=====
print("\n" + "=" * 60)
print("🔍 检索测试：我爱吃苹果")
print("=" * 60)

results = collection.query(
    query_texts=["我爱吃苹果"],
    n_results=3,
)

print("Top 3 最相似的文档：")
for doc, dist, meta in zip(
    results["documents"][0],
    results["distances"][0],
    results["metadatas"][0],
):
    print(f"  距离={dist:.3f} | 类别={meta['category']} | 内容：{doc}")

# 💡 distance 越小越相似（注意跟昨天的 similarity 相反！）


# ===== 5. 带元数据过滤的检索（这是 ChromaDB 比手撸强的地方 =====
print("\n" + "=" * 60)
print("🔍 带过滤的检索：只搜 food 类别")
print("=" * 60)

results = collection.query(
    query_texts=["苹果"],
    n_results=3,
    where={"category":"food"},  # 🔑 只在food 里搜
)

for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f" 类别={meta['category']} | 内容: {doc}")

# ===== 6. 查看集合统计 =====
print(f"\n 集合中共有 {collection.count()} 条文档")


# ===== 7. 持久化验证 =====
print(f"\n💡 关键验证：")
print(f"  现在 Ctrl+C 终止程序，再运行一次")
print(f"  数据不会重复（因为 id 相同会更新而不是插入）")
print(f"  但数据永远保留在 {DB_PATH}")
