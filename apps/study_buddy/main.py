"""
StudyBuddy - Web 服务（最小版）
🎯 暴露 4 个核心 API
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .extractor import extract_knowledge, save_knowledge_points
from .reviewer import get_due_knowledge_points, update_review_result, get_stats
from .quiz import generate_quiz, grade_answer
from .profile import build_user_profile
from .models import SessionLocal, KnowledgePoint
from .vectorstore import find_similar_points, sync_all_from_db 


app = FastAPI(title="StudyBuddy 🧠")


# ===================== 数据模型 =====================
class ChatRequest(BaseModel):
    message: str


class AnswerRequest(BaseModel):
    point_id: int
    question: str
    user_answer: str


# ===================== API 1: 学习（提取知识点）=====================
@app.post("/learn")
def learn(req: ChatRequest):
    """💡 用户发一句话 → 提取知识点 → 入库"""
    points = extract_knowledge(req.message)
    saved = save_knowledge_points(req.message, points)
    return {
        "extracted_count": len(saved),
        "points": [
            {"id": p.id, "topic": p.topic, "content": p.content, "difficulty": p.difficulty}
            for p in saved
        ],
    }


# ===================== API 2: 获取今日复习 =====================
@app.get("/due")
def due():
    """📅 今天该复习的知识点 + 自动出题"""
    points = get_due_knowledge_points(limit=10)
    
    quizzes = []
    for p in points:
        quizzes.append({
            "point_id": p.id,
            "topic": p.topic,
            "difficulty": p.difficulty,
            "question": generate_quiz(p),
            "_correct_point": p.content,  # 🔒 前端用不到，但要传给判分
        })
    
    return {"total": len(quizzes), "quizzes": quizzes}


# ===================== API 3: 提交回答 =====================
@app.post("/answer")
def answer(req: AnswerRequest):
    """✅ 用户答题 → AI 判分 → 更新数据库"""
    # 取回原知识点
    db = SessionLocal()
    try:
        point = db.query(KnowledgePoint).get(req.point_id)
        if not point:
            raise HTTPException(404, "知识点不存在")
        correct_point = point.content
    finally:
        db.close()
    
    # 判分
    result = grade_answer(req.question, correct_point, req.user_answer)
    
    # 更新数据库
    updated = update_review_result(req.point_id, result["correct"])
    
    return {
        "correct": result["correct"],
        "feedback": result["feedback"],
        "new_mastery": updated.mastery,
        "next_review_at": updated.next_review_at.isoformat(),
    }


# ===================== API 4: 学习画像 =====================
@app.get("/profile")
def profile():
    """🧠 用户的学习画像"""
    return build_user_profile()


# ===================== API 5: 简单统计 =====================
@app.get("/stats")
def stats():
    """📊 快速统计"""
    return get_stats()


# ===================== API 6: 向量库同步 =====================
@app.post("/sync_vectors")
def sync_vectors():
    return sync_all_from_db()


# ===================== API 7: 相似知识点搜索 =====================
@app.get("/search")
def search(q: str, top_k: int = 5):
    """🔍 语义搜索知识点
    
    例: /search?q=依赖注入
    """
    results = find_similar_points(q, top_k=top_k)
    return {"query": q, "results": results}


# ===================== 简易首页（明天会改成完整 UI）=====================
@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <html>
    <head><title>StudyBuddy 🧠</title></head>
    <body style="font-family: sans-serif; max-width: 800px; margin: 50px auto;">
        <h1>🧠 StudyBuddy API</h1>
        <p>明天会有完整的 Web UI。现在你可以测试这些 API：</p>
        <ul>
            <li><a href="/profile">/profile</a> - 你的学习画像</li>
            <li><a href="/stats">/stats</a> - 快速统计</li>
            <li><a href="/due">/due</a> - 今日待复习（注意：会调 LLM 出题，等几秒）</li>
            <li><a href="/docs">/docs</a> - 完整 API 文档</li>
        </ul>
    </body>
    </html>
    """