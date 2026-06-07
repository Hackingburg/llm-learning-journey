"""
ResumeAI - 三步分析链
🎯 把"专家思维过程"封装成 Prompt
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 三个核心 Prompt（这是 ResumeAI 的核心） =====

PROMPT_STEP1_ANALYZE = """你是一个资深 HR，请用 5 句话提炼这份简历的核心信息：

简历内容：
{resume_text} 

请输出：
1. 候选人最强的 1 个标签
2. 主要技术栈（最多 5 个）
3. 核心项目/工作成果（最多 3 条）
4. 看起来的求职意向
5. 简历整体印象（一句话）"""


PROMPT_STEP2_MATCH = """你是面试官，对比候选人和岗位需求：

【候选人画像】
{candidate_summary}

【目标岗位】
{target_position}

请输出：
✅ 匹配度：X/10 分（一句话理由）
💪 候选人 3 大优势：
    1.
    2.
    3.
⚠️ 3 个需要补强的点（重要！）：
    1.
    2.
    3.
🎯 应聘成功率：低/中/高（一句话理由）"""


PROMPT_STEP3_REWRITE = """你是一个顶级简历优化师。基于以下分析，请给出**3 条具体可执行**的修改建议：

【匹配分析】
{match_result}

【原简历】
{resume_text}

请给出 3 条建议，每条包含：
🔧 建议 N：
   ❌ 原文：（引用原简历的具体段落）
   ✅ 改成：（给出修改后的版本）
   💡 为什么：（一句话理由）

⚠️ 必须给出可直接复制粘贴的修改版文字，不要泛泛而谈！"""


# ===== LLM 调用（流式） =====
def stream_llm(prompt:str):
    """流式调用 DeepSeek，逐字返回"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": 0.3,
        },
        stream=True,
        timeout=120,
    )

    full_text = ""
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
                full_text += content
                yield content
        except json.JSONDecodeError:
            continue
    
    yield None # 结束标记
    return full_text


# ===== 三步分析主流程（生成器，逐步 yield 结果）=====
def analyze_resume(resume_text:str, target_position: str):
    """🌟 ResumeAI 的核心：三步分析链
    
    yield 格式：
    {"step": 1, "type": "stream", "content": "..."}  # 流式增量
    {"step": 1, "type": "done", "full": "完整结果"}  # 步骤完成
    """
    results = {}

    # === step 1: 分析简历 ===
    yield {"step": 1, "type": "start", "title": "🗒️ 第一步：解读简历"}

    prompt1 = PROMPT_STEP1_ANALYZE.format(resume_text=resume_text)
    step1_text = ""
    for chunk in stream_llm(prompt1):
        if chunk is None:
            break
        step1_text += chunk
        yield {"step": 1, "type": "stream", "content": chunk}

    results["step1"] = step1_text
    yield {"step": 1, "type": "done", "full": step1_text}

    # === step 2: 匹配岗位 ===
    yield {"step": 2, "type": "start", "title": "🎯 第二步：岗位匹配分析"}

    prompt2 = PROMPT_STEP2_MATCH.format(candidate_summary=step1_text, target_position=target_position,)
    step2_text = ""
    for chunk in stream_llm(prompt2):
        if chunk is None:
            break
        step2_text += chunk
        yield {"step": 2, "type": "stream", "content": chunk}

    results["step2"] = step2_text
    yield {"step": 2, "type": "done", "full": step2_text}

    # === step 3: 优化建议 === 
    yield {"step": 3, "type": "start", "title": "🔧 第三步：简历优化建议"}

    prompt3 = PROMPT_STEP3_REWRITE.format(match_result=step2_text, resume_text=resume_text)
    step3_text = ""
    for chunk in stream_llm(prompt3):
        if chunk is None:
            break
        step3_text += chunk
        yield {"step": 3, "type": "stream", "content": chunk}

    results["step3"] = step3_text
    yield {"step": 3, "type": "done", "full": step3_text}

    # === 完成 ===
    yield {"type": "complete", "results": results}


# ===== 命令行测试 =====
if __name__ == "__main__":
    sample_resume = """# 王兴

## 个人简介
3年Python开发经验

## 工作经验
2023-至今 ABC公司 后端工程师
- 用FastAPI开发后端API
- 用过MySQL和Redis

## 技能
Python, FastAPI, MySQL, Redis
"""

    sample_job = "我们招聘高级LLM应用工程师，要求：3年以上Python经验，熟悉RAG、Function Calling，会向量数据库，能独立部署。"

    for event in analyze_resume(sample_resume, sample_job):
        if event.get("type") == "start":     
            print(f"\n{'='*60}")
            print(event["title"])
            print('='*60)
        elif event.get("type") == "stream":
            print(event["content"], end="", flush=True)
        elif event.get("type") == "done":
            print() # 换行