"""
PR Reviewer - 评论格式化
🎯 把审查结果转成适合发到 GitHub 的 Markdown
"""
from datetime import datetime


COMMENT_HEADER = """## 🤖 AI Code Review

> 由 [PR Reviewer](https://github.com/Hackingburg/llm-learning-journey) 自动生成 · {timestamp}
> Powered by DeepSeek + Python

---
"""


COMMENT_FOOTER = """
---

<details>
<summary>💡 关于这次审查</summary>

- 本评论由 AI 自动生成，仅供参考
- 不能完全替代人工 code review
- 重大决策请以人工判断为准

</details>
"""


def format_review_as_comment(
    pr_info: dict,
    file_reviews: list[dict],
    summary: str,
    max_files_inline: int = 5,
) -> str:
    """
    把审查结果格式化为 GitHub 评论 Markdown
    
    设计原则：
    - 总结放最上面（最重要的先看）
    - 文件数 ≤ max_files_inline 时全展开
    - 文件数 > max_files_inline 时折叠
    """
    parts = []
    
    # 1. 头部
    parts.append(COMMENT_HEADER.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))
    
    # 2. 整体总结（最重要，放前面）
    parts.append("### 🎯 整体总结\n")
    parts.append(summary)
    parts.append("\n\n---\n")
    
    # 3. 各文件审查
    parts.append(f"### 📋 文件审查（共 {len(file_reviews)} 个）\n")
    
    use_collapsed = len(file_reviews) > max_files_inline
    
    for idx, fr in enumerate(file_reviews, 1):
        filename = fr["filename"]
        review = fr["review"]
        additions = fr.get("additions", 0)
        deletions = fr.get("deletions", 0)
        stats = f"+{additions} / -{deletions}"
        
        if use_collapsed:
            # 文件多 → 折叠
            parts.append(
                f"<details>\n"
                f"<summary><code>{filename}</code> ({stats})</summary>\n\n"
                f"{review}\n\n"
                f"</details>\n"
            )
        else:
            # 文件少 → 全展开
            parts.append(f"\n#### {idx}. `{filename}` <sub>{stats}</sub>\n")
            parts.append(review)
            parts.append("\n")
    
    # 4. 尾部
    parts.append(COMMENT_FOOTER)
    
    return "\n".join(parts)


# ===== 测试 =====
if __name__ == "__main__":
    fake_pr = {
        "title": "feat: add date option",
        "author": "Hackingburg",
        "additions": 22,
        "deletions": 0,
    }
    fake_files = [
        {
            "filename": "map_to_image.py",
            "additions": 22,
            "deletions": 0,
            "review": "## ✅ 做得好\n- 参数命名清晰\n\n## 🐛 问题\n- 无\n\n## 💡 建议\n- 可加 type hint",
        },
    ]
    fake_summary = "## 🎯 总体评价\n小而精的改动\n\n## ✅ 推荐：APPROVE"
    
    output = format_review_as_comment(fake_pr, fake_files, fake_summary)
    print(output)
    print("\n" + "="*60)
    print(f"📏 评论总长度: {len(output)} 字符")