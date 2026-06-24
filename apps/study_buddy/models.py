"""
StudyBuddy - 数据模型
🎯 用 SQLAlchemy 存学习知识点 + 复习记录
"""
from datetime import datetime
from pathlib import Path
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = Path("data/study_buddy.db")
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class KnowledgePoint(Base):
    """🧠 学到的知识点"""
    __tablename__ = "knowledge_points"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic = Column(String, index=True)         # 主题，如 "SQLAlchemy"
    content = Column(Text)                      # 内容，如 "declarative_base 是..."
    difficulty = Column(String, default="中等")  # 简单/中等/困难
    raw_message = Column(Text)                  # 用户原话（便于追溯）
    
    # 📅 学习记录
    learned_at = Column(DateTime, default=datetime.now, index=True)
    
    # 🔄 复习状态（艾宾浩斯遗忘曲线）
    review_count = Column(Integer, default=0)              # 已复习次数
    last_reviewed_at = Column(DateTime, nullable=True)     # 最后复习时间
    next_review_at = Column(DateTime, default=datetime.now, index=True)  # 下次复习时间
    
    # 📊 掌握度（0-1，越高越熟练）
    mastery = Column(Float, default=0.0)

    # 🆕 向量化标记（在 ChromaDB 里的 ID）
    embedded = Column(Integer, default=0)  # 0=未向量化, 1=已向量化
    
    def __repr__(self):
        return f"<KnowledgePoint {self.topic}: {self.content[:30]}...>"


class StudySession(Base):
    """📝 学习会话（每次和 buddy 聊天的记录）"""
    __tablename__ = "study_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_message = Column(Text)
    ai_response = Column(Text)
    extracted_count = Column(Integer, default=0)  # 这次提取了几个知识点
    created_at = Column(DateTime, default=datetime.now, index=True)


Base.metadata.create_all(engine)


# ===== 测试 =====
if __name__ == "__main__":
    db = SessionLocal()
    try:
        # 插入一条假数据
        kp = KnowledgePoint(
            topic="SQLAlchemy",
            content="declarative_base 是 ORM 基类",
            difficulty="中等",
            raw_message="今天学了 SQLAlchemy 的 declarative_base",
        )
        db.add(kp)
        db.commit()
        
        # 查出来
        all_kp = db.query(KnowledgePoint).all()
        print(f"📚 知识点总数：{len(all_kp)}")
        for k in all_kp:
            print(f"  - {k.topic}: {k.content}")
    finally:
        db.close()