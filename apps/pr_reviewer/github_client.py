"""
PR Reviewer - GitHub 客户端 (Day 19 升级版)
🎯 解析 PR URL -> 拉取 diff 信息
🆕 加入 token 支持 + 限流检测 + 友好错误
"""
import re
import os
import requests
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# ===== 自定义异常 =====
class GitHubAPIError(Exception):
    """GitHub API 调用异常基类"""
    pass


class RateLimitError(GitHubAPIError):
    """限流异常"""
    def __init__(self, reset_time: int=0):
        self.reset_time = reset_time
        super().__init__(f"API 请求过于频繁，请稍后再试 (重置时间: {reset_time} 秒)")


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
        "X-GitHub-Api-Version": "2022-11-28", # 🆕 明确指定 API 版本
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers



def _check_response(response: requests.Response) -> None:
    """🆕 统一的响应检查"""
    # 限流（403 + 特定 header）
    if response.status_code == 403:
        remanining = response.headers.get("X-RateLimit-Remaining")
        if remanining == "0":
            import time
            reset = int(response.headers.get("X-RateLimit-Reset", 0))
            wait_seconds = max(0, reset - int(time.time()))
            raise RateLimitError(wait_seconds)
        
    # PR 不存在
    if response.status_code == 404:
        raise GitHubAPIError("PR 不存在或无访问权限")
    
    # 其他错误
    if not response.ok:
        raise GitHubAPIError(f"GitHub API 错误: {response.status_code} - {response.text}")
    
        
def get_pr_info(owner: str, repo: str, pr_number: int) -> dict:
    """获取 PR 基本信息"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=_headers(), timeout=30)
    _check_response(response)

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
        # 🆕 加一个"PR 唯一标识"，给缓存用
        "head_sha": data["head"]["sha"],
    }


def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    """获取 PR 中变更的所有文件 + 每个文件的 diff"""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=_headers(), timeout=30)
    _check_response(response)

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


def get_rate_limit_status() -> dict:
    """🆕 查看当前 API 限额状态（调试用）"""
    response = requests.get(
        "https://api.github.com/rate_limit",
        headers=_headers(),
        timeout=10
    )
    response.raise_for_status()
    core = response.json()["resources"]["core"]
    return {
        "limit": core["limit"],
        "remaining": core["remaining"],
        "used": core["used"],
        "reset_in_seconds": max(0, core["reset"] - int(__import__("time").time())),
    }

# ===== 测试 =====
if __name__ == "__main__":
    # 先看看限额状态
    status = get_rate_limit_status()
    print(f"📊 GitHub API 限额：{status['remaining']}/{status['limit']} 次")
    print(f"   {'✅ 配置了 Token (5000/h)' if status['limit'] > 100 else '⚠️ 未配置 Token (60/h)'}")
    print()
    
    # 测试 PR 解析
    test_url = "https://github.com/originalankur/maptoposter/pull/221"
    info = parse_pr_url(test_url)
    print(f"📋 解析结果: {info}\n")
    
    try:
        pr = get_pr_info(**info)
        print(f"📌 标题: {pr['title']}")
        print(f"👤 作者: {pr['author']}")
        print(f"📊 +{pr['additions']} / -{pr['deletions']} / {pr['changed_files']} 文件")
        print(f"🔖 head_sha: {pr['head_sha'][:8]}...")  # 🆕 缓存用
    except GitHubAPIError as e:
        print(f"❌ {e}")