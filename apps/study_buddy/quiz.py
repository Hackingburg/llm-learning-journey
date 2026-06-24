"""
StudyBuddy - 智能出题 + 判分（含关联式出题）
🎯 生成普通题与关联式（融合）题，并对用户回答判分
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

# ====== 基本 Prompt ======
QUIZ_PROMPT = """你是学习陪伴助手。基于下面的知识点，出一道**简短的考题**。

【知识点】
主题: {topic}
内容: {content}
难度: {difficulty}

要求：
1. 题目要**简短**（1-2 句话，最多 30 字）
2. 难度要匹配："简单"→直接问定义；"中等"→问应用场景；"困难"→问对比/原理
3. 答案应该是**一句话能说清**的（不要让用户写长篇）
4. 不要直接抄知识点的原文，要换个说法考查

只返回考题文字，不要任何前缀（如"题目："），不要带答案."""
GRADE_PROMPT = """你是宽容但严谨的老师。判断学生回答是否正确。

【考题】{question}
【标准答案要点】{correct_point}
【学生回答】{user_answer}

判断规则：
- 抓"核心意思"对不对，不要纠结措辞
- 答对核心 → 即使表达不完美也算对
- 关键概念错或方向错 → 算错
- 不会、跳过、空白 → 算错

请返回 JSON：
{
  "correct": true/false,
  "feedback": "一句话点评（如果错了，告诉正确答案；如果对了，可以补充延伸知识）"
}

只返回 JSON.
"""

# ===== 新增：关联式出题 Prompt =====
ASSOCIATED_QUIZ_PROMPT = """你是一个高级技术面试出题人。请基于以下**主知识点**和若干**相关知识点**，生成一道能考察“融会贯通/应用能力”的简短题目。

【主知识点】
主题: {topic}
内容: {content}
难度: {difficulty}

【相关知识点】
{related_texts}

要求：
1. 生成一道一至两句的题目（最多 40 字），能考察理解与应用，不要仅是定义复述。
2. 题目应该明确可以用一句话作答（不要让人写长篇）。
3. 若相关知识点可以组合成具体代码场景（例如把 session 注入到路由），请优先出这样的应用题。
4. 返回 JSON：{ "question": "...", "rationale": "一句话说明为什么选这个题目" }
5. 只返回 JSON，不要额外文字.
"""

def generate_quiz(point) -> str:
    """🎲 给单个知识点出题（原先实现）"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": QUIZ_PROMPT.format(
                    topic=point.topic,
                    content=point.content,
                    difficulty=point.difficulty,
                ),
            }],
            "temperature": 0.7,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

def generate_associated_quiz(point, related_points: list[dict]) -> dict:
    """
    🎯 生成关联式题目
    - point: KnowledgePoint ORM 对象（主知识点）
    - related_points: list of dicts from vectorstore.find_similar_points, each has 'content','topic'
    返回：{"question": "...", "rationale": "..."} 或 None（失败）
    """
    related_texts = "\n".join(
        [f"- {r['topic']}: {r['content']}" for r in related_points[:5]]
    ) if related_points else ""
    prompt = ASSOCIATED_QUIZ_PROMPT.format(
        topic=point.topic,
        content=point.content,
        difficulty=point.difficulty,
        related_texts=related_texts or "(无相关知识点)",
    )
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        data = json.loads(text)
        return {
            "question": data.get("question", "").strip(),
            "rationale": data.get("rationale", "").strip(),
        }
    except Exception as e:
        print("⚠️ generate_associated_quiz 失败:", e)
        return None

def grade_answer(question: str, correct_point: str, user_answer: str) -> dict:
    """✅ 判断用户回答对不对（原有实现）"""
    if not user_answer.strip():
        return {"correct": False, "feedback": "你没有作答，正确答案是：" + correct_point}
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": GRADE_PROMPT.format(
                    question=question,
                    correct_point=correct_point,
                    user_answer=user_answer,
                ),
            }],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
    try:
        result = json.loads(text)
        return {
            "correct": bool(result.get("correct", False)),
            "feedback": result.get("feedback", "（无评语）"),
        }
    except json.JSONDecodeError:
        return {"correct": False, "feedback": "判分失败，原文：" + text[:120]}