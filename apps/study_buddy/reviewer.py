"""
StudyBuddy - 复习调度器
🎯 找出今天该复习的知识点 + 更新复习记录
"""
from datetime import datetime, timedelta
from .models import SessionLocal, KnowledgePoint


# ===== 白宾浩斯遗忘曲线（复用 extractor.py 的） =====
REVIEW_INTERVALS_DAYS = [1, 3, 7, 15, 30, 60, 120]


def calculate_next_interval(review_count: int, was_correct:bool) -> int:
    """
    🧠 智能下次间隔
    
    - 答对 -> 按曲线推进到下一档
    - 答错 -> 回退到上一档（说明掌握度不够）
    """
    if was_correct:
        idx = min(review_count, len(REVIEW_INTERVALS_DAYS) - 1)
    else:
        # 答错就退一档（不低于 1 天）
        idx = max(0, review_count - 1)
    return REVIEW_INTERVALS_DAYS[idx]


def get_due_knowledge_points(limit: int = 10) -> list[KnowledgePoint]:
    """📅 获取今天该复习的知识点"""
    db = SessionLocal()
    try:
        now = datetime.now()
        points = (
            db.query(KnowledgePoint)
            .filter(KnowledgePoint.next_review_at <= now)
            .filter(KnowledgePoint.mastery < 1.0)  # 只复习掌握度 < 1 的
            .order_by(KnowledgePoint.next_review_at.asc())
            .limit(limit)
            .all()
        )
        # 🛡️ 把对象"脱离会话", 避免 session 关了之后访问报错
        db.expunge_all()
        return points
    finally:
        db.close()


def update_review_result(point_id: int, was_correct: bool) -> KnowledgePoint:
    """✅ 更新一条知识点的复习结果"""
    db = SessionLocal()
    try:
        kp = db.query(KnowledgePoint).get(point_id)
        if not kp:
            raise ValueError(f"知识点 {point_id} 不存在")
        
        # 更新复习次数和掌握度
        kp.review_count += 1
        kp.last_reviewed_at = datetime.now()

        days = calculate_next_interval(kp.review_count, was_correct)
        kp.next_review_at = datetime.now() + timedelta(days=days)
        
        # 简单的掌握度计算：答对 -> +0.2, 答错 -> -0.1, 保持在 [0, 1]
        if was_correct:
            kp.mastery = min(1.0, kp.mastery + 0.2)
        else:
            kp.mastery = max(0.0, kp.mastery - 0.1)
        
        db.commit()
        db.refresh(kp)
        db.expunge(kp)  # 脱离会话
        return kp
    finally:
        db.close()


def get_stats() -> dict:
    """📊 获取一些统计数据"""
    db = SessionLocal()
    try:
        total = db.query(KnowledgePoint).count()
        due = (
            db.query(KnowledgePoint)
            .filter(KnowledgePoint.next_review_at <= datetime.now())
            .filter(KnowledgePoint.mastery < 1.0)
            .count()
        )
        mastered = db.query(KnowledgePoint).filter(KnowledgePoint.mastery >= 1.0).count()

        # 平均掌握度
        all_points = db.query(KnowledgePoint).all()
        avg_mastery = sum(p.mastery for p in all_points) / len(all_points) if all_points else 0

        return {
            "total": total,
            "due": due,
            "mastered": mastered,
            "avg_mastery": round(avg_mastery, 2),
        }
    finally:
        db.close()

# ===== 测试 =====
if __name__ == "__main__":
    print("📊 当前学习状态：")
    stats = get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n🔍 今天该复习的知识点：")
    due = get_due_knowledge_points()
    if not due:
        print("  🎉 今天没有要复习的！要么全掌握了，要么还没到时间")
    else:
        for p in due:
            print(f"  📚 [{p.difficulty}] {p.topic}: {p.content}")
            print(f"     掌握度: {p.mastery:.0%} | 已复习: {p.review_count} 次")