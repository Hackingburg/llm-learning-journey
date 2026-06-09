"""
PR Reviewer - GitHub 客户端
🎯 解析 PR URL -> 拉取 diff 信息
"""
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def parse_pr_url(url: str) -> dict:
    """
    解析 PR URL -> {owner, repo, pr_number}
    
    支持格式：
    - https://github.com/owner/repo/pull/123
    - https://github.com/owner/repo/pull/123/files
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError("无效的 PR URL")
    return {
        "owner": match.group(1),
        "repo": match.group(2),
        "pr_number": int(match.group(3)),
    }


def _headers() -> dict:
    """构造请求头（带可选 token）"""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "PR-Reviewer/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def get_pr_info(owner: str, repo: str, pr_number: int) -> dict:
    """获取 PR 基本信息"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()
    data = response.json()
    return {
        "title": data["title"],
        "body": data["body"] or "(无描述)",
        "author": data["user"]["login"],
        "state": data["state"],
        "additions": data["additions"],
        "deletions": data["deletions"],
        "changed_files": data["changed_files"],
        "url": data["html_url"],
    }


def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """获取 PR 中变更的所有文件 + 每个文件的 diff"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()

    files = response.json()
    return [
        {
            "filename": item["filename"],
            "status": item["status"],
            "additions": item["additions"],
            "deletions": item["deletions"],
            "patch": item.get("patch", ""),  # 🌟 diff 文本
        } 
        for item in files
    ]


# ===== 测试 =====
if __name__ == "__main__":
    # 用一个真实的小 PR 测试
    test_url = "https://github.com/fastapi/fastapi/pull/12000"
    # ⚠️ 如果你没创建过 PR，换一个你看到的小 PR，比如：
    # test_url = "https://github.com/fastapi/fastapi/pull/12000"
    
    info = parse_pr_url(test_url)
    print(f"📋 解析结果: {info}")
    
    try:
        pr = get_pr_info(**info)
        print(f"\n📌 标题: {pr['title']}")
        print(f"👤 作者: {pr['author']}")
        print(f"📊 +{pr['additions']} / -{pr['deletions']} / {pr['changed_files']} 文件\n")
        
        files = get_pr_files(**info)
        for f in files[:3]:  # 只看前 3 个文件
            print(f"📄 {f['filename']} ({f['status']})")
            print(f"   diff 前 200 字: {f['patch'][:200]}")
            print()
    except requests.HTTPError as e:
        print(f"❌ API 错误: {e}")
        print("💡 可能是 PR 不存在，或限流。换一个公开 PR 试试")