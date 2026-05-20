"""
Day 11-3: 多文档 RAG + 元数据过滤
🎯 真实场景：HR 文档、技术文档分类管理
"""
from day11_rag_chromadb import ChromaRAG

# 用一个新集合（避免和任务 2 数据混在一起）
rag = ChromaRAG(db_path="data/chroma_multi", collection_name="company_kb")

# ===== 入库多个文档 =====
print("📚 构建公司知识库...")
rag.ingest("data/hr_policy.txt", source_name="hr")
rag.ingest("data/tech_stack.txt", source_name="tech")
rag.ingest("data/my_docs.txt", source_name="personal")

print(f"\n✅ 共入库 {rag.collection.count()} 个片段\n")


# ===== 测试 1：全库检索 =====
print("=" * 60)
print("🧪 测试 1：全库检索")
print("=" * 60)
rag.ask("请假需要提前几天？")


# ===== 测试 2：⭐ 元数据过滤 =====
print("\n" + "=" * 60)
print("🧪 测试 2：只在 HR 文档里搜")
print("=" * 60)
rag.ask("报销有什么规则？", where={"source": "hr"})


# ===== 测试 3：⭐ 关键对比 =====
print("\n" + "=" * 60)
print("🧪 测试 3：同样问题，不同范围对比")
print("=" * 60)

print("\n--- A. 在 HR 文档搜'技术栈'---")
rag.ask("我们用什么技术栈？", where={"source": "hr"})

print("\n--- B. 在 tech 文档搜'技术栈'---")
rag.ask("我们用什么技术栈？", where={"source": "tech"})

print("\n💡 关键洞察：")
print("   元数据过滤 = 让 RAG 系统支持'分库'，是企业级 RAG 必备能力")
print("   用户登录后只能查自己有权限的文档 → 信息安全")