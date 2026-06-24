"""
StudyBuddy - 智能出题 + 判分
🎯 把知识点变成考题，再判断用户回答对不对
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


# ===== 出题 Prompt =====
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

只返回考题文字，不要任何前缀（如"题目："），不要带答案。"""


# ===== 判分 Prompt =====
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
{{
  "correct": true/false,
  "feedback": "一句话点评（如果错了，告诉正确答案；如果对了，可以补充延伸知识）"
}}

只返回 JSON。"""


def generate_quiz(point) -> str:
    """🎲 给一个知识点出考题"""
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
            "temperature": 0.7,  # 出题要多样化
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()


def grade_answer(question: str, correct_point: str, user_answer: str) -> dict:
    """✅ 判断用户回答对不对"""
    # 用户输入为空 → 直接算错
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
            "temperature": 0.1,  # 判分要稳定
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
        # 兜底
        return {"correct": False, "feedback": "判分失败，原文：" + text[:100]}


# ===== 完整交互式测试 =====
if __name__ == "__main__":
    from .reviewer import get_due_knowledge_points, update_review_result
    
    due = get_due_knowledge_points(limit=3)
    if not due:
        print("🎉 没有要复习的知识点。先去 extractor.py 测试，存几条进来")
        exit()
    
    print(f"📚 今天要复习 {len(due)} 个知识点\n")
    
    for idx, point in enumerate(due, 1):
        print(f"\n{'='*60}")
        print(f"题目 {idx}/{len(due)}  [{point.difficulty}]  主题: {point.topic}")
        print('='*60)
        
        # 出题
        question = generate_quiz(point)
        print(f"\n🎲 {question}")
        
        # 用户回答
        user_answer = input("\n你的回答（直接回车跳过）: ").strip()
        
        # 判分
        result = grade_answer(question, point.content, user_answer)
        
        if result["correct"]:
            print(f"\n✅ 答对了！{result['feedback']}")
        else:
            print(f"\n❌ 不太对。{result['feedback']}")
        
        # 更新数据库
        updated = update_review_result(point.id, result["correct"])
        next_date = updated.next_review_at.strftime("%Y-%m-%d")
        print(f"\n📊 掌握度: {updated.mastery:.0%} | 下次复习: {next_date}")
    
    print(f"\n{'='*60}")
    print("🎊 今天复习完成！")