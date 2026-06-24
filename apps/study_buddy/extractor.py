"""
StudyBuddy - 知识点提取器
🎯 从用户的随意聊天中，让LLM 自动提取结构化知识点
"""
import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .models import SessionLocal, KnowledgePoint, StudySession

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")


EXTRACT_PROMPT = """你是学习陪伴助手，要从用户的话里提取"学到的知识点"。

用户说："{message}

请输出 JSON 数组 （-定要是合法 JSON）。规则：
1. 如果用户在描述学到的东西 -> 提取出来
2. 如果只是闲聊/提问/抱怨 -> 返回空数组 []
3. 每条知识点要"原子化" --一条只讲一件事
4. 难度判断：
   - 简单：常识、基础语法
   - 中等： 需要理解的概念
   - 困难： 深度原理、需要练习的技能
   
JSON 格式：
[
  {{
    "topic": "主题（一个词，如'SQLALchemy')",
    "content": "知识点内容（一句话）",
    "difficulty": "难度（简单/中等/困难）"
  }}
]

只返回 JSON， 不要任何其他文字。
"""


def extract_knowledge(message: str) -> list[dict]:
    """🎯 用 LLM 从用户消息中提取知识点"""
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": EXTRACT_PROMPT.format(message=message)},
            ],
            "temperature": 0.1, # 提取任务用低温度
            "response_format": {"type": "json_object"}, # 🆕 强制 JSON
        },
        timeout=60,
    )
    response.raise_for_status()

    text = response.json()["choices"][0]["message"]["content"]

    # LLM 有时返回 {"items": [...]} 而不是裸数组，做个兼容
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
        return []
    except json.JSONDecodeError:
        return []
    

# ===== 艾宾浩斯遗忘曲线（简化版） =====
REVIEW_INTERVALS_DAYS = [1, 3, 7, 15, 30]  # 第 N 次复习的间隔


def calculate_next_review(review_count: int) -> datetime:
    """计算下次复习时间"""
    if review_count >= len(REVIEW_INTERVALS_DAYS):
        days = REVIEW_INTERVALS_DAYS[-1]
    else:
        days = REVIEW_INTERVALS_DAYS[review_count]
    return datetime.now() + timedelta(days=days)


def save_knowledge_points(message: str, points: list[dict]) -> list[KnowledgePoint]:
    """ 💾 把提取的知识点存进库"""
    db = SessionLocal()
    saved = []
    try:
        for p in points:
            kp = KnowledgePoint(
                topic=p.get("topic", "未分类"),
                content=p.get("content", ""),
                difficulty=p.get("difficulty", "中等"),
                raw_message=message,
                next_review_at=calculate_next_review(0), 
            )
            db.add(kp)
            saved.append(kp)
        db.commit()
        for kp in saved:
            db.refresh(kp)
    finally:
        db.close()
    return saved 


# ===== 测试 =====
if __name__ == "__main__":
    test_messages = [
        "今天学了 SQLAlchemy 的 declarative_base，还学了 sessionmaker 是用来创建会话工厂的",
        "在吗？随便聊聊",  # 应该返回 []
        "Python 的 functools.partial 可以预先填好函数参数，特别适合给 callback 用",
    ]
    
    for msg in test_messages:
        print(f"\n💬 用户：{msg}")
        points = extract_knowledge(msg)
        if not points:
            print("  📭 没提取到知识点（闲聊/提问/抱怨）")
        else:
            for p in points:
                print(f"  📚 [{p.get('difficulty')}] {p.get('topic')}: {p.get('content')}")
            
            # 存进库
            saved = save_knowledge_points(msg, points)
            print(f"  💾 已存入 {len(saved)} 条")