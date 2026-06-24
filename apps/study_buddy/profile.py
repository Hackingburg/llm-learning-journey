"""
StudyBuddy - 学习画像
🎯 用数据"画"出用户的学习全貌
"""
from datetime import datetime, timedelta 
from collections import defaultdict
from .models import SessionLocal, KnowledgePoint


def build_user_profile() -> dict:
    """🧠 构建学习画像"""
    db = SessionLocal()
    try:
        all_points = db.query(KnowledgePoint).all()

        if not all_points:
            return {
                "total_points": 0,
                "message": "还没有学习记录，去和 StudyBuddy 聊聊吧！",
            }
        
        # ===== 1. 基础统计 =====
        total = len(all_points)
        mastered = [p for p in all_points if p.mastery >= 0.8]
        in_progress = [p for p in all_points if 0 < p.mastery < 0.8]
        weak = [p for p in all_points if p.review_count > 0 and p.mastery < 0.3]

        # ===== 2. 按主题聚合 =====
        topics = defaultdict(list)
        for p in all_points:
            topics[p.topic].append(p)

        topic_stats = {}
        for topic, points in topics.items():
            sorted_by_mastery = sorted(points, key=lambda p: p.mastery, reverse=True)
            topic_stats[topic] = {
                "count": len(points),
                "avg_mastery": round(sum(p.mastery for p in points) / len(points), 2),
                "strongest": sorted_by_mastery[0].content[:40] + "...",
                "weakest": sorted_by_mastery[-1].content[:40] + "..." if len(points) > 1 else None,
            }

          # 按 count 排序（学得最多的主题排前面）
        topic_stats = dict(sorted(topic_stats.items(), key=lambda x: x[1]["count"], reverse=True))
        
        # ===== 3. 学习连续天数 =====
        study_dates = {p.learned_at.date() for p in all_points}
        sorted_dates = sorted(study_dates, reverse=True)
        
        streak = 0
        today = datetime.now().date()
        check_date = today
        for d in sorted_dates:
            if d == check_date:
                streak += 1
                check_date -= timedelta(days=1)
            elif d == check_date - timedelta(days=1):
                # 跳过昨天还没学的情况（今天还没学也算 0 起步）
                check_date = d - timedelta(days=1)
                streak += 1
            else:
                break
        
        # ===== 4. 整合输出 =====
        return {
            "total_points": total,
            "mastered_count": len(mastered),
            "in_progress_count": len(in_progress),
            "weak_count": len(weak),
            "topics": topic_stats,
            "study_streak_days": streak,
            "last_study_date": sorted_dates[0].isoformat() if sorted_dates else None,
            "average_mastery": round(sum(p.mastery for p in all_points) / total, 2),
        }
    finally:
        db.close()    
        
              
# ===== 测试 =====
if __name__ == "__main__":
    import json
    profile = build_user_profile()
    print("🧠 你的学习画像：")
    print("="*60)
    print(json.dumps(profile, ensure_ascii=False, indent=2))