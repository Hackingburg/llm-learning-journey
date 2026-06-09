"""
PR Reviewer - AI 审查核心
🎯 用 LLM 分析单个文件的 diff
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 单文件审查 Prompt =====
REVIEW_PROMPT = """你是一个经验丰富的高级工程师，正在审查一个 Pull Request 中的单个文件的改动。

【文件信息】
文件名：{filename}
状态：{status} (added=新增 / modified=修改 / removed=删除)
变更行数： +{additions} / -{deletions}

【Diff 内容】
```diff 
{patch}
```

请严格按以下格式输出（如果某项没有，就写"无"):

## ✅ 做得好的地方
- （1-2 条， 简短）

## 🐛 潜在问题
- （列出有问题的具体行 + 为什么）
- （重点关注：安全漏洞、空指针、资源泄漏、并发问题、错误处理）

## 💡 改进建议
- （1-3 条可执行的具体建议）

## 📊 风险等级
[低 / 中 / 高] - 一句话理由

⚠️ 重点关注真正的问题，不要为了凑数说一些无关痛痒的话。
⚠️ 如果文件改动很小且没问题，可以简短回答。"""


# ===== 整体总结 Prompt =====
SUMMARY_PROMPT = """你是高级工程师，已经审查完一个 PR 的所有文件。请给出整体评价：

【PR 信息】
标题：{title}
描述：{body}
作者：{author}
总改动： +{additions} / -{deletions} / {changed_files} 个文件

【各文件审查结果摘要】
{file_reviews}

请输出：

## 🎯 PR 总体评价
[一句话总结]

## ✅ 推荐决定
- [APPROVE / REQUEST CHANGES / COMMENT]
- 理由：（一句话）

## 🔑 核心反馈
- （3 条最重要的反馈，按优先级排序）

## 💬 建议给作者的话
（一段友好的话，2—3 句）"""


# ===== 流式调用 LLM =====
def stream_llm(prompt: str, temperature: float = 0.3):
    """流式调用 Deepseek，逐字返回"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={ "Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": temperature,
        },
        stream=True,
        timeout=120,
    )
    response.raise_for_status()

    for line in response.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            data = json.loads(data_str)
            content = data["choices"][0]["delta"].get("content", "")
            if content:
                yield content
        except json.JSONDecodeError:
            continue


# ===== 审查单个文件 ===== 
def review_single_file(file_info: dict):
    """审查单个文件，生成器，yield 流式增量"""
    patch = file_info.get("patch", "")

    # 边界 1: 没有 patch（二进制文件等）
    if not patch:
        yield "（无 diff 内容，可能是二进制文件、重命名或文件太大）"    
        return
    
    # 边界 2: diff 太长 -> 截断防止超 token
    if len(patch) > 6000:
        patch = patch[:6000] + "\n\n[...diff 过长被截断...]"

    prompt = REVIEW_PROMPT.format(
        filename=file_info["filename"],
        status=file_info["status"],
        additions=file_info["additions"],
        deletions=file_info["deletions"],
        patch=patch,
    )

    for chunk in stream_llm(prompt):
        yield chunk


# ===== 生成整体总结 =====
def review_summary(pr_info: dict, file_reviews_summary: str):
    """生成 PR 整体总结"""
    prompt = SUMMARY_PROMPT.format(
        title=pr_info["title"],
        body=pr_info["body"][:500],  # 截断描述防止超 token
        author=pr_info["author"],
        additions=pr_info["additions"],
        deletions=pr_info["deletions"],
        changed_files=pr_info["changed_files"],
        file_reviews=file_reviews_summary[:3000],  # 截断文件审查摘要防止超 token
    )

    for chunk in stream_llm(prompt):
        yield chunk


# ===== 测试 =====
if __name__ == "__main__":
    # 模拟一个简单的diff（包含 SQL 注入修复）
    fake_file = {
        "filename": "auth.py",
        "status": "modified",
        "additions": 5,
        "deletions": 1,
        "patch": """@@ -10,7 +10,11 @@ def login(username, password):
-    user = db.query(f"SELECT * FROM users WHERE name='{username}'")
+    # SQL 注入修复：用参数化查询
+    user = db.query("SELECT * FROM users WHERE name=?", (username,))
+    if not user:
+        return None
     return user
""",
    }
    
    print("🤖 AI 审查中...\n")
    for chunk in review_single_file(fake_file):
        print(chunk, end="", flush=True)
    print("\n\n✅ 完成")