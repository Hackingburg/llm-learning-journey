"""
Day 8-2: SQLAlchemy 入门 - 用 Python 类代替 SQL
目标：理解 ORM （Object-Relational Mapping）
"""
from datetime import datetime 
from pathlib import Path 
from sqlalchemy import create_engine, Column, Integer, String, DateTime, select
from sqlalchemy.orm import declarative_base, sessionmaker

# ===== 1. 连接数据库 =====
DB_PATH = Path("data/day08_orm.db")
DB_PATH.parent.mkdir(exist_ok=True)

# echo=True 会打印 SQLAlachemy 自动生成的 SQL（学习时打开很有用）
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# Session 是“数据库操作的会话”， 跟 LLM 的 session 不是一回事
SessionLocal = sessionmaker(bind=engine)

# Base 是所有 ORM 模型的父类
Base = declarative_base()


# ===== 2. 定义“表” - 用 Python 类！ =====
class Note(Base):
    """笔记表 - 看，跟 Pydantic 类长得很像"""
    __tablename__ = "notes" 

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Note id={self.id} title='{self.title}'>"



# ===== 3. 创建表（建表语句自动生成） =====
Base.metadata.create_all(engine)
print("✅ 表已创建")


# ===== 4. 操作数据 - 全部用 Python 对象 =====

# ----- 插入 -----
with SessionLocal() as session:
    note1 = Note(title="学 SQLAlchemy", content="今天学了 ORM")
    note2 = Note(title="学 FastAPI", content="昨天搞定了 Web服务")

    session.add(note1)
    session.add(note2)
    session.commit() # 🔑 提交才真正写入
    print(f"✅ 插入了 2 条笔记，note1.id = {note1.id}")

# ----- 查询 -----
with SessionLocal() as session:
    # 查所有
    print("\n📋 所有笔记：")
    notes = session.execute(select(Note)).scalars().all()
    for note in notes:
        print(f" [{note.id}] {note.title} - {note.content}")

    # 按条件查（推荐写法）
    print("\n📋 标题包含 '学' 的笔记:")
    stmt = select(Note).where(Note.title.like("%学%"))
    for note in session.execute(stmt).scalars():
        print(f" {note}")

# ----- 更新 -----
with SessionLocal() as session:
    note = session.execute(select(Note).where(Note.title == "学 FastAPI")).scalar_one_or_none()
    
    if note: 
        note.content = "FastAPI + DeepChat 服务化完成 ✅"
        session.commit()
        print(f"\n✅ 已更新笔记：{note.content}")

# ----- 删除 （演示用，注释掉避免真删  -----
# with SessionLocal() as session:
#     note = session.execute(select(Note).where(Note.id == 1)).scalar_one
#     session.delete(note)
#     session.commit() 


print("\n💡 对比体验：")
print("  - 没写一句 SQL， 全是 Python")
print("  - 改字段名/换数据库，代码不用大改")
print("  - 类型校验全自动")


