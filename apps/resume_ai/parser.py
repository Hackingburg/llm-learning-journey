"""
ResumeAI - 简历解析器
🎯 把不同格式的简历 → 统一的文本
"""
from pathlib import Path


def parse_resume(content: str, filename: str = "") -> dict:
    """
    解析简历文本，返回结构化信息
    
    第一版：先支持 .txt / .md（PDF 下周再加）
    返回：{raw_text, sections, word_count}
    """
    if not content.strip():
        raise ValueError("简历内容为空")
    
    # 按章节分割（识别 # 标题或常见关键词）
    sections = {}
    current_section = "其他"
    current_lines = []
    
    common_section_keywords = [
        "教育", "教育背景", "学历",
        "工作", "工作经验", "项目经历", "项目经验",
        "技能", "技术栈",
        "证书", "荣誉",
        "个人简介", "自我介绍", "关于我",
    ]
    
    for line in content.split("\n"):
        stripped = line.strip()
        
        # Markdown 标题
        if stripped.startswith("#"):
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped.lstrip("#").strip()
            current_lines = []
            continue
        
        # 中文关键词标题
        if any(kw in stripped for kw in common_section_keywords) and len(stripped) < 20:
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped
            current_lines = []
            continue
        
        current_lines.append(line)
    
    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()
    
    return {
        "raw_text": content,
        "sections": sections,
        "word_count": len(content),
        "section_count": len(sections),
    }


# ===== 测试 =====
if __name__ == "__main__":
    sample = """# 王兴

## 个人简介
后端工程师，3年经验

## 工作经验
2023-至今 ABC公司 Python工程师
- 负责后端API开发

## 技能
Python, FastAPI, MySQL
"""
    
    result = parse_resume(sample)
    print(f"📊 字数: {result['word_count']}")
    print(f"📚 章节数: {result['section_count']}")
    for name, content in result["sections"].items():
        print(f"\n【{name}】")
        print(content[:80])