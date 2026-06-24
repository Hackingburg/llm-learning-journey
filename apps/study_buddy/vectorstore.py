"""
StudyBuddy - 向量存储
🎯 把知识点变成向量，用 ChromaDB 存储
🎯 支持"找相似知识点"
"""
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from .models import SessionLocal, KnowledgePoint


# ===== 配置 =====
CHROMA_DIR = Path("data/study_buddy_chroma")
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# 多语言模型（支持中英文混搭， 64MB 左右）
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# 单例：避免每次调用都重新加载模型（加载要5-10秒）
_model = None
_collection = None


def _get_model():
    """🎓 懒加载 embedding 模型"""
    global _model
    if _model is None:
        print(f"加载向量化模型 {MODEL_NAME} ...")
        _model = SentenceTransformer(MODEL_NAME)
        print("✅ 模型加载完成")
    return _model

def _get_collection():
    """🗂️ 懒加载 ChromaDB collection"""
    global _collection
    if _collection is None:
        print(f"连接 ChromaDB 数据库 {CHROMA_DIR} ...")
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # collection 名称和表名保持一致
        _collection = client.get_or_create_collection("knowledge_points", metadata={"description": "StudyBuddy 知识点向量存储"})
        print("✅ ChromaDB 连接完成")
    return _collection

def embed_text(text: str) -> list[float]:
    """📐 文本向量化"""
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


# ===================== 增 =====================
def add_knowledge_point(point: KnowledgePoint) -> None:
    """➕ 把一个知识点加入向量库"""
    collection = _get_collection()

    # 把 topic 和 content 拼起来一起 embed（信息更丰富）
    text = f"{point.topic} {point.content}"
    vector = embed_text(text)

    collection.upsert(  # 🆕 用 upsert 防重复
        ids=[str(point.id)],
        embeddings=[vector],
        documents=[text],
        metadatas=[{
            "topic": point.topic,
            "content": point.content,
            "difficulty": point.difficulty,
            "kp_id": point.id,
        }],
    )


# ===================== 查 =====================
def find_similar_points(query: str, top_k: int = 5, exclude_ids: list[int] = None) -> list[dict]:
    """🔍 找相似知识点"""
    collection = _get_collection()

    # 检查是否有数据
    if collection.count() == 0:
        return []
    
    query_vector = embed_text(query)

    # 多查几条，因为可能要排除某些 id
    n_results = top_k + len(exclude_ids or [])

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(n_results, collection.count()),  # 多查一些，后面再排除
    )

    exclude_ids = set(exclude_ids or [])
    similar = []

    for i, doc_id in enumerate(results["ids"][0]):
        kp_id = int(doc_id)
        if kp_id in exclude_ids:
            continue

        similar.append({
            "id": kp_id,
            "text": results["documents"][0][i],
            "topic": results["metadatas"][0][i]["topic"],
            "content": results["metadatas"][0][i]["content"],
            "distance": results["distances"][0][i],
            "similarity": 1 - results["distances"][0][i],  # 距离转相似度
        })

        if len(similar) >= top_k:
            break

    return similar


def sync_all_from_db() -> dict:
    """🔄 把数据库里所有"未向量化"的知识点同步到向量库"""
    db = SessionLocal()
    try:
        unembedded = db.query(KnowledgePoint).filter(KnowledgePoint.embedded == 0).all()
        
        if not unembedded:
            return {"synced": 0, "total_in_vector_db": _get_collection().count()}
        
        print(f"🔄 正在向量化 {len(unembedded)} 个知识点...")
        for p in unembedded:
            add_knowledge_point(p)
            p.embedded = 1
        
        db.commit()
        print("✅ 同步完成")
        
        return {
            "synced": len(unembedded),
            "total_in_vector_db": _get_collection().count(),
        }
    finally:
        db.close()


# ===== 测试 =====
if __name__ == "__main__":
    # 1. 把数据库所有知识点同步到向量库
    print("=" * 60)
    print("🔄 同步数据库 → 向量库")
    print("=" * 60)
    result = sync_all_from_db()
    print(f"📊 {result}")
    
    # 2. 测试相似度搜索
    print("\n" + "=" * 60)
    print("🔍 测试语义搜索")
    print("=" * 60)
    
    test_queries = [
        "FastAPI 怎么实现依赖注入？",
        "数据库 ORM 是啥",
        "Python 高阶函数",
    ]
    
    for query in test_queries:
        print(f"\n💬 查询: {query}")
        results = find_similar_points(query, top_k=3)
        if not results:
            print("  📭 没找到")
        else:
            for r in results:
                print(f"  📚 [{r['similarity']:.2f}] {r['topic']}: {r['content'][:50]}...")