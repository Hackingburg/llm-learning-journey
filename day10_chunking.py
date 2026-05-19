"""
Day 10-2: 文本分块 - RAG 系统的"切书"环节
目标：把长文档切成可以独立检索的小段
"""
from pathlib import Path

def simple_chunking(text: str, chunk_size: int = 200, overlap: int = 50) -> list[str]:
    """
    最简单的分块：按字数切，相邻块有重叠
    
    Args：
        text: 原始文本
        chunk_size: 每块多少字
        overlap：相邻块重叠多少字（避免切断关键信息）
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk.strip())
        start += chunk_size -overlap # 🔑 步进 = 块大小 - 重叠
    return chunks 

def chunk_by_paragraph(text: str) -> list[str]:
    """
    按段落分块（用空行分隔）
    通常比按字数切效果更好，因为保留了语义完整性
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def main():
    # 读取文档
    doc_path = Path("data/my_docs.txt")
    if not doc_path.exists():
        print("❌ 找不到 data/my_docs.txt，请先创建")
        return 
    
    text = doc_path.read_text(encoding="utf-8")
    print(f" 原始文档长度：{len(text)} 字符\n")

    # ===== 方法 1：按字数 =====
    print("=" * 60)
    print("🧪 方法 1：按字数分块（size=150, overlap=30) ")
    print("=" * 60)
    chunks_a = simple_chunking(text, chunk_size=150, overlap=30)
    print(f"切成了 {len(chunks_a)} 块\n")
    for i, c in enumerate(chunks_a, 1):
        print(f"--- 块 {i}（{len(c)} 字）---")
        print(c[:80] + "..." if len(c) > 80 else c)
        print()
    
    # ===== 方法 2：按段落 =====
    print("=" * 60)
    print("🧪 方法 2：按段落分块（推荐）")
    print("=" * 60)
    chunks_b = chunk_by_paragraph(text)
    print(f"切成了 {len(chunks_b)} 块\n")
    for i, c in enumerate(chunks_b, 1):
        print(f"--- 块 {i}（{len(c)} 字）---")
        print(c[:80] + "..." if len(c) > 80 else c)
        print()
    
    print("💡 工程建议：")
    print("   - 中文文档：300-500 字/块 比较平衡")
    print("   - 代码文档：按函数/类分块更好")
    print("   - 复杂结构：用 LangChain 的 RecursiveCharacterTextSplitter")


if __name__ == "__main__":    
    main()
