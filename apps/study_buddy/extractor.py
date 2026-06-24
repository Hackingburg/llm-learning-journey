"""
StudyBuddy - 提取器（含后台向量同步）
🎯 从用户消息里提取知识点并保存；新增后台线程把新知识点上到向量库
"""
import os
import json
import requests
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .models import SessionLocal, KnowledgePoint

load_dotenv()
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY")

EXTRACT_PROMPT = """你是学习陪伴助手，要从用户的话里提取"学到的知识点"。

用户说："{message}"

请输出 JSON 数组（一定要是合法 JSON）。规则：
1. 如果用户在描述学到的东西 → 提取出来
2. 如果只是闲聊/提问/抱怨 → 返回空数组 []
3. 每条知识点要"原子化"——一条只讲一件事
4. 难度判断：
   - 简单：常识、基础语法
   - 中等：需要理解的概念
   - 困难：深度原理、需要练习的技能

JSON 格式：
[
  {
    "topic": "主题（一个词，如 'SQLAlchemy'）",
    "content": "知识点内容（一句话）",
    "difficulty": "简单/中等/困难"
  }
]

只返回 JSON，不要任何其他文字。
"""

def extract_knowledge(message: str) -> list[dict]:
    """🎯 用 LLM 从用户消息中提取知识点"""
    # 使用 replace 而不是 str.format，避免 prompt 里的 JSON 花括号被误解析
    prompt = EXTRACT_PROMPT.replace("{message}", message)

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    response.raise_for_status()
    text = response.json()["choices"][0]["message"]["content"]
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

# ===== 艾宾浩斯遗忘曲线（简化版）=====
REVIEW_INTERVALS_DAYS = [1, 3, 7, 15, 30]

def calculate_next_review(review_count: int) -> datetime:
    if review_count >= len(REVIEW_INTERVALS_DAYS):
        days = REVIEW_INTERVALS_DAYS[-1]
    else:
        days = REVIEW_INTERVALS_DAYS[review_count]
    from datetime import datetime, timedelta
    return datetime.now() + timedelta(days=days)

def save_knowledge_points(message: str, points: list[dict]) -> list[KnowledgePoint]:
    """💾 把提取的知识点存进库，并在后台异步向量化"""
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
                embedded=0,
            )
            db.add(kp)
            saved.append(kp)
        db.commit()
        for kp in saved:
            db.refresh(kp)
    finally:
        db.close()

    # 异步后台把刚存的知识点同步到向量库，避免阻塞
    def _bg_sync(kps):
        try:
            from .vectorstore import add_knowledge_point
            for kp in kps:
                try:
                    add_knowledge_point(kp)
                    db2 = SessionLocal()
                    try:
                        obj = db2.query(KnowledgePoint).get(kp.id)
                        if obj:
                            obj.embedded = 1
                            db2.commit()
                    finally:
                        db2.close()
                except Exception as e:
                    print("⚠️ 单条向量化失败:", e)
        except Exception as e:
            print("⚠️ 向量化后台同步失败:", e)

    t = threading.Thread(target=_bg_sync, args=(saved,), daemon=True)
    t.start()
    return saved

# ===== 测试 =====
if __name__ == "__main__":
    test_messages = [
        "今天学了 SQLAlchemy 的 declarative_base，还学了 sessionmaker 是用来创建会话工厂的",
        "在吗？随便聊聊",
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
            saved = save_knowledge_points(msg, points)
            print(f"  💾 已存入 {len(saved)} 条")