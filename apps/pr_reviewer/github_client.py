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

def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> dict:
    """
    在 PR 上发表评论
    
    ⚠️ 需要 token 有 public_repo 权限
    ⚠️ PR 的 issue_comment 接口实际是用 /issues/{pr_number}/comments 因为 GitHub 把 PR 当成特殊的 Issue
    
    返回： 评论的完整信息（含 html_url）
    """
    if not GITHUB_TOKEN:
        raise GitHubAPIError("发表评论需要配置 GITHUB_TOKEN")
    
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    response = requests.post(
        url,
        headers=_headers(),
        json={"body": body},
        timeout=30,
        proxies={"http": None, "https": None},  # 🆕 显式禁用代理
    )
    _check_response(response)

    data = response.json()
    return {
        "id": data["id"],
        "html_url": data["html_url"],
        "created_at": data["created_at"],
    }


def list_my_comments(owner: str, repo: str, pr_number: int) -> list[dict]:
    """🆕 列出当前 token 用户在这个 PR 下发过的评论（用于幂等）"""
    if not GITHUB_TOKEN:
        return []
    
    # 先拿到当前 token 对应的用户名
    me_resp = requests.get("https://api.github.com/user", headers=_headers(), timeout=10)
    if not me_resp.ok:
        return []
    my_login = me_resp.json()["login"]
    
    # 拉这个 PR 的所有评论
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    response = requests.get(url, headers=_headers(), timeout=30)
    response.raise_for_status()
    
    return [ 
        {"id": c["id"], "body": c["body"], "html_url": c["html_url"]}
        for c in response.json()
        if c["user"]["login"] == my_login
    ]
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

    print("\n" + "="*60)
    confirm = input("🧪 要测试发一条评论吗？(y/N): ")
    if confirm.lower() == "y":
        try:
            result = post_pr_comment(
                owner="Hackingburg",  # ⚠️ 改成你自己的仓库（测试用）
                repo="llm-learning-journey",
                pr_number=1,  # ⚠️ 改成你的某个 PR 号
                body="🤖 这是 PR Reviewer 的测试评论，请忽略。",
            )
            print(f"✅ 评论已发布: {result['html_url']}")
        except Exception as e:
            print(f"❌ 失败: {e}")