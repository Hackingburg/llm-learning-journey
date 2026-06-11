"""
PR Reviewer - Web 服务（Day 19 升级版）
🎯 加入缓存 + 重试 + 历史接口
"""
import json
import anyio
from functools import partial
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from .github_client import parse_pr_url, get_pr_info, get_pr_files, GitHubAPIError, RateLimitError
from .reviewer import review_single_file, review_summary
from .cache import make_cache_key, get_cached_review, save_review, list_cached_reviews


app = FastAPI(title="PR Reviewer 🤖")


class ReviewRequest(BaseModel):
    pr_url: str
    force_refresh: bool = False  # 🆕 强制刷新缓存


def sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/review")
async def review(req: ReviewRequest):
    """主入口：流式 AI 审查（带缓存）"""
    try:
        info = parse_pr_url(req.pr_url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    async def stream():
        # === 1. 拉 PR 信息（先拿到 head_sha 才能查缓存）===
        yield sse_event("status", {"message": "🔍 正在获取 PR 信息..."})
        
        try:
            pr_info = await anyio.to_thread.run_sync(partial(get_pr_info, **info))
        except RateLimitError as e:
            yield sse_event("error", {"message": str(e)})
            return
        except GitHubAPIError as e:
            yield sse_event("error", {"message": f"获取 PR 失败: {e}"})
            return
        
        yield sse_event("pr_info", pr_info)
        
        # === 2. 🆕 查缓存 ===
        cache_key = make_cache_key(
            info["owner"], info["repo"], info["pr_number"], pr_info["head_sha"]
        )
        
        if not req.force_refresh:
            cached = get_cached_review(cache_key)
            if cached:
                yield sse_event("status", {"message": f"⚡ 命中缓存（{cached['cached_at']}）"})
                
                # 回放缓存的文件审查
                for idx, fr in enumerate(cached["file_reviews"], 1):
                    yield sse_event("file_start", {
                        "index": idx,
                        "total": len(cached["file_reviews"]),
                        "filename": fr["filename"],
                        "additions": fr.get("additions", 0),
                        "deletions": fr.get("deletions", 0),
                    })
                    yield sse_event("file_stream", {"index": idx, "content": fr["review"]})
                    yield sse_event("file_done", {"index": idx})
                
                # 回放总结
                yield sse_event("summary_start", {})
                yield sse_event("summary_stream", {"content": cached["summary"]})
                yield sse_event("done", {"from_cache": True})
                return
        
        # === 3. 拉文件列表 ===
        try:
            files = await anyio.to_thread.run_sync(partial(get_pr_files, **info))
        except GitHubAPIError as e:
            yield sse_event("error", {"message": f"获取文件失败: {e}"})
            return
        
        yield sse_event("status", {"message": f"📊 找到 {len(files)} 个变更文件"})
        
        review_files = [f for f in files if f.get("patch")][:10]
        if len(files) > 10:
            yield sse_event("status", {
                "message": f"⚠️ 文件太多，只审查前 10 个（实际 {len(files)} 个）"
            })
        
        # === 4. 逐个文件审查 ===
        file_reviews_for_cache = []  # 🆕 用于缓存
        files_summaries = []
        
        for idx, file_info in enumerate(review_files, 1):
            yield sse_event("file_start", {
                "index": idx,
                "total": len(review_files),
                "filename": file_info["filename"],
                "additions": file_info["additions"],
                "deletions": file_info["deletions"],
            })
            
            full_review = ""
            try:
                gen = review_single_file(file_info)
                while True:
                    chunk = await anyio.to_thread.run_sync(next, gen, None)
                    if chunk is None:
                        break
                    full_review += chunk
                    yield sse_event("file_stream", {"index": idx, "content": chunk})
            except Exception as e:
                yield sse_event("file_stream", {
                    "index": idx,
                    "content": f"\n❌ 审查失败: {e}",
                })
                full_review += f"\n❌ 审查失败: {e}"
            
            yield sse_event("file_done", {"index": idx})
            
            # 🆕 记录到缓存
            file_reviews_for_cache.append({
                "filename": file_info["filename"],
                "additions": file_info["additions"],
                "deletions": file_info["deletions"],
                "review": full_review,
            })
            files_summaries.append(f"【{file_info['filename']}】\n{full_review[:500]}")
        
        # === 5. 整体总结 ===
        yield sse_event("summary_start", {})
        
        full_summary = ""
        try:
            gen = review_summary(pr_info, "\n\n".join(files_summaries))
            while True:
                chunk = await anyio.to_thread.run_sync(next, gen, None)
                if chunk is None:
                    break
                full_summary += chunk
                yield sse_event("summary_stream", {"content": chunk})
        except Exception as e:
            yield sse_event("summary_stream", {"content": f"\n❌ 总结失败: {e}"})
        
        # === 6. 🆕 保存到缓存 ===
        try:
            save_review(
                cache_key=cache_key,
                owner=info["owner"],
                repo=info["repo"],
                pr_number=info["pr_number"],
                head_sha=pr_info["head_sha"],
                pr_info=pr_info,
                file_reviews=file_reviews_for_cache,
                summary=full_summary,
            )
        except Exception as e:
            print(f"⚠️ 缓存保存失败: {e}")  # 不影响用户
        
        yield sse_event("done", {"from_cache": False})
    
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/history")
def history():
    """🆕 查看历史审查列表"""
    return list_cached_reviews(limit=20)


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_HTML


# ⚠️ 前端 HTML 沿用 Day 18 的，加 2 处小改动：
# 1. 在 input-area 加一个 "强制重新审查" 复选框
# 2. 处理 done 事件时显示是不是来自缓存

FRONTEND_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PR Reviewer 🤖</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; padding: 20px; }
.container { max-width: 1000px; margin: 0 auto; }
.header { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 24px; margin-bottom: 16px; }
.header h1 { font-size: 24px; color: #58a6ff; }
.header p { color: #8b949e; margin-top: 6px; font-size: 14px; }
.input-area { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.input-row { display: flex; gap: 10px; }
#prUrl { flex: 1; padding: 10px; background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; font-family: inherit; font-size: 14px; }
#prUrl:focus { outline: none; border-color: #58a6ff; }
button { padding: 10px 24px; background: #238636; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }
button:disabled { background: #444; cursor: not-allowed; }
button:hover:not(:disabled) { background: #2ea043; }
.options { margin-top: 10px; color: #8b949e; font-size: 13px; }
.options input { margin-right: 6px; }
.pr-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.pr-card h2 { color: #58a6ff; font-size: 16px; }
.pr-card .meta { color: #8b949e; font-size: 13px; margin-top: 6px; }
.status { background: #1c2128; border-left: 3px solid #58a6ff; padding: 10px 14px; margin-bottom: 12px; border-radius: 4px; font-size: 13px; color: #8b949e; }
.status.cache { border-left-color: #d29922; color: #d29922; }
.file-review { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
.file-review .filename { color: #58a6ff; font-family: monospace; font-size: 14px; margin-bottom: 8px; font-weight: 600; }
.file-review .stats { color: #8b949e; font-size: 12px; margin-bottom: 12px; }
.file-review .content { white-space: pre-wrap; line-height: 1.7; font-size: 13px; color: #c9d1d9; }
.summary { background: #1f6feb15; border: 2px solid #58a6ff; border-radius: 8px; padding: 20px; margin-top: 20px; }
.summary h2 { color: #58a6ff; margin-bottom: 12px; }
.summary .content { white-space: pre-wrap; line-height: 1.7; font-size: 14px; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 PR Reviewer - AI 代码审查助手</h1>
        <p>粘贴任何公开的 GitHub PR 链接，AI 立即给你专业 review。同一 commit 走缓存。</p>
    </div>
    
    <div class="input-area">
        <div class="input-row">
            <input id="prUrl" placeholder="https://github.com/owner/repo/pull/123" />
            <button id="reviewBtn" onclick="review()">🚀 审查</button>
        </div>
        <div class="options">
            <label><input type="checkbox" id="forceRefresh" />强制重新审查（忽略缓存）</label>
        </div>
    </div>
    
    <div id="output"></div>
</div>

<script>
let currentFileDiv = null;
let currentSummaryDiv = null;

async function review() {
    const url = document.getElementById("prUrl").value.trim();
    const force = document.getElementById("forceRefresh").checked;
    const btn = document.getElementById("reviewBtn");
    const output = document.getElementById("output");
    
    if (!url) { alert("请输入 PR 链接"); return; }
    
    btn.disabled = true;
    btn.textContent = "审查中...";
    output.innerHTML = "";
    currentFileDiv = null;
    currentSummaryDiv = null;
    
    try {
        const res = await fetch("/review", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({pr_url: url, force_refresh: force}),
        });
        
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, {stream: true});
            const events = buffer.split("\\n\\n");
            buffer = events.pop();
            
            for (const evt of events) {
                const lines = evt.split("\\n");
                let type = "", data = "";
                for (const line of lines) {
                    if (line.startsWith("event: ")) type = line.slice(7);
                    if (line.startsWith("data: ")) data = line.slice(6);
                }
                if (!type) continue;
                const obj = JSON.parse(data);
                handle(type, obj);
            }
        }
    } catch (e) {
        alert("出错: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "🚀 审查";
    }
}

function handle(type, obj) {
    const output = document.getElementById("output");
    
    if (type === "status") {
        const d = document.createElement("div");
        d.className = "status" + (obj.message.includes("缓存") ? " cache" : "");
        d.textContent = obj.message;
        output.appendChild(d);
    }
    else if (type === "pr_info") {
        const d = document.createElement("div");
        d.className = "pr-card";
        d.innerHTML = `
            <h2>📌 ${obj.title}</h2>
            <div class="meta">
                👤 ${obj.author} · 📊 +${obj.additions}/-${obj.deletions} · 📁 ${obj.changed_files} 文件
                · <a href="${obj.url}" target="_blank" style="color: #58a6ff;">在 GitHub 查看 ↗</a>
            </div>
        `;
        output.appendChild(d);
    }
    else if (type === "error") {
        const d = document.createElement("div");
        d.className = "status";
        d.style.borderLeftColor = "#f85149";
        d.textContent = "❌ " + obj.message;
        output.appendChild(d);
    }
    else if (type === "file_start") {
        currentFileDiv = document.createElement("div");
        currentFileDiv.className = "file-review";
        currentFileDiv.innerHTML = `
            <div class="filename">📄 [${obj.index}/${obj.total}] ${obj.filename}</div>
            <div class="stats">+${obj.additions} / -${obj.deletions}</div>
            <div class="content"></div>
        `;
        output.appendChild(currentFileDiv);
    }
    else if (type === "file_stream" && currentFileDiv) {
        currentFileDiv.querySelector(".content").textContent += obj.content;
        window.scrollTo(0, document.body.scrollHeight);
    }
    else if (type === "summary_start") {
        currentSummaryDiv = document.createElement("div");
        currentSummaryDiv.className = "summary";
        currentSummaryDiv.innerHTML = `<h2>🎯 整体审查总结</h2><div class="content"></div>`;
        output.appendChild(currentSummaryDiv);
    }
    else if (type === "summary_stream" && currentSummaryDiv) {
        currentSummaryDiv.querySelector(".content").textContent += obj.content;
        window.scrollTo(0, document.body.scrollHeight);
    }
    else if (type === "done") {
        const d = document.createElement("div");
        d.className = "status";
        d.style.borderLeftColor = "#3fb950";
        d.textContent = obj.from_cache 
            ? "✅ 审查完成（来自缓存 ⚡）" 
            : "✅ 审查完成（新鲜出炉 🔥）";
        output.appendChild(d);
    }
}
</script>
</body>
</html>
"""