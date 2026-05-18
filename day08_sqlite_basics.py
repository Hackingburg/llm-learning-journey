"""
Day 8-1: SQLite 入门 - 用纯 SQL 理解数据库
目标：掌握 CRUD 4 个基本动作
"""
import sqlite3
from pathlib import Path

# ===== 1. 连接数据库（不存在就自动创建一个 .db 文件） =====
DB_PATH = Path("data/day08_demo.db")
DB_PATH.parent.mkdir(exist_ok=True) 

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"✅ 已连接数据库：{DB_PATH}")


# ===== 2. 建表（Create） =====
# 如果表已经存在就跳过
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER,
    email TEXT UNIQUE
)
""")
print("✅ 已创建表：users")


# ===== 3. 插入数据（Insert） =====
# 用 ？占位符，避免 SQL 注入（重要！）
try:
    cursor.execute(
        "INSERT INTO users (name, age, email) VALUES (?, ?, ?)",
        ("Alice", 30, "alice@example.com")
    )
    cursor.execute(
        "INSERT INTO users (name, age, email) VALUES (?, ?, ?)",
        ("Bob", 25, "bob@example.com")
    )
    conn.commit() # 🔑 必须 commit 才会真正写入
    print("✅ 已插入数据：Alice 和 Bob")
except sqlite3.IntegrityError as e:
    print(f"⚠️ 数据已存在：{e}")


# ===== 4. 查询数据（SELECT） =====
print("\n📋 所有用户：")
cursor.execute("SELECT id, name, age, email FROM users")
for row in cursor.fetchall():
    print(f" {row}")

# 带条件查询
print("\n📋 年龄 > 28 的用户：")
cursor.execute("SELECT name, age FROM users WHERE age > ?", (28,))
for row in cursor.fetchall():
    print(f" {row}")


# ===== 5. 更新数据（UPDATE) =====
cursor.execute("UPDATE users SET age = ? WHERE name = ?", (31, "Alice"))
conn.commit()
print("\n✅ 已更新 Alice 的年龄")

# 验证
cursor.execute("SELECT name, age FROM users WHERE name = ?", ("Alice",))
print(f"📋 Alice 的信息： {cursor.fetchone()}")

# ===== 6. 删除数据（DELETE) =====
# 注意：实际生产很少真删，通常加 deleted_at字段做“软删除”
# cursor.execute("DELETE FROM users WHERE name = ?", ("Bob",))
# conn.commit()



# ===== 7. 关闭连接 =====
conn.close()
print("\n✅ 已关闭数据库连接")
print(f"\n💡 数据被持久化到{DB_PATH} (大小: {DB_PATH.stat().st_size} bytes)，下次运行依然存在")