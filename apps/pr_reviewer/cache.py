"""
PR Reviewer - SQLite 缓存
🎯 同一个 PR commit 不重复审查，省钱省时
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager


CACHE_DB = Path("data/pr_review_cache.db")
CACHE_DB.parent.mkdir(exist_ok=True)


@contextmanager
def _db():
    """SQLite 连接的上下文管理器"""
    conn = sqlite3.connect(CACHE_DB)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """初始化缓存表"""
    with _db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS review_cache (
                cache_key TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                head_sha TEXT NOT NULL,
                pr_info_json TEXT NOT NULL,
                file_reviews_json TEXT NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 🆕 给查询常用字段建索引
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr 
            ON review_cache(owner, repo, pr_number)
        """)


def make_cache_key(owner: str, repo: str, pr_number: int, head_sha: str) -> str:
    """🔑 缓存 key：带 head_sha → PR 推新 commit 自动失效"""
    return f"{owner}/{repo}#{pr_number}@{head_sha[:12]}"


def get_cached_review(cache_key: str) -> dict | None:
    """读取缓存，没有就返回 None"""
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM review_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        
        if not row:
            return None
        
        return {
            "cache_key": row["cache_key"],
            "pr_info": json.loads(row["pr_info_json"]),
            "file_reviews": json.loads(row["file_reviews_json"]),
            "summary": row["summary"],
            "cached_at": row["created_at"],
        }


def save_review(
    cache_key: str,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    pr_info: dict,
    file_reviews: list,
    summary: str,
) -> None:
    """保存审查结果到缓存"""
    with _db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO review_cache
            (cache_key, owner, repo, pr_number, head_sha, pr_info_json, file_reviews_json, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                owner,
                repo,
                pr_number,
                head_sha,
                json.dumps(pr_info, ensure_ascii=False),
                json.dumps(file_reviews, ensure_ascii=False),
                summary,
            ),
        )


def list_cached_reviews(limit: int = 20) -> list[dict]:
    """🆕 列出最近的缓存（用于前端展示历史）"""
    with _db() as conn:
        rows = conn.execute(
            """
            SELECT cache_key, owner, repo, pr_number, head_sha, created_at,
                   pr_info_json
            FROM review_cache
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        
        return [
            {
                "cache_key": r["cache_key"],
                "owner": r["owner"],
                "repo": r["repo"],
                "pr_number": r["pr_number"],
                "head_sha": r["head_sha"][:8],
                "title": json.loads(r["pr_info_json"])["title"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]


# 模块加载时自动建表
init_db()


# ===== 测试 =====
if __name__ == "__main__":
    # 模拟保存一个审查
    save_review(
        cache_key="test/repo#1@abc12345",
        owner="test",
        repo="repo",
        pr_number=1,
        head_sha="abc1234567890",
        pr_info={"title": "测试 PR", "author": "tester"},
        file_reviews=[{"filename": "test.py", "review": "✅ 看起来不错"}],
        summary="整体评价：通过",
    )
    print("✅ 已保存测试数据")
    
    # 读出来
    cached = get_cached_review("test/repo#1@abc12345")
    print(f"\n📦 读到缓存: {cached['summary']}")
    
    # 列表
    print("\n📋 最近审查列表:")
    for r in list_cached_reviews():
        print(f"  - {r['title']} ({r['head_sha']})")
        