"""
PR Reviewer - Web 服务（Day 19+ 历史侧边栏版）
🎯 加入缓存 + 重试 + Token + 侧边栏历史
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
    force_refresh: bool = False


def sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ===================== API: 流式审查 =====================
@app.post("/review")
async def review(req: ReviewRequest):
    try:
        info = parse_pr_url(req.pr_url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    async def stream():
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
        cache_key = make_cache_key(info["owner"], info["repo"], info["pr_number"], pr_info["head_sha"])

        # === 缓存命中（流式回放）===
        if not req.force_refresh:
            cached = get_cached_review(cache_key)
            if cached:
                yield sse_event("status", {"message": f"⚡ 命中缓存（{cached['cached_at']}）"})
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
                yield sse_event("summary_start", {})
                yield sse_event("summary_stream", {"content": cached["summary"]})
                yield sse_event("done", {"from_cache": True, "cache_key": cache_key})
                return

        # === 拉文件列表 ===
        try:
            files = await anyio.to_thread.run_sync(partial(get_pr_files, **info))
        except GitHubAPIError as e:
            yield sse_event("error", {"message": f"获取文件失败: {e}"})
            return

        yield sse_event("status", {"message": f"📊 找到 {len(files)} 个变更文件"})
        review_files = [f for f in files if f.get("patch")][:10]
        if len(files) > 10:
            yield sse_event("status", {"message": f"⚠️ 文件太多，只审查前 10 个（实际 {len(files)} 个）"})

        file_reviews_for_cache = []
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
                err = f"\n❌ 审查失败: {e}"
                yield sse_event("file_stream", {"index": idx, "content": err})
                full_review += err
            yield sse_event("file_done", {"index": idx})
            file_reviews_for_cache.append({
                "filename": file_info["filename"],
                "additions": file_info["additions"],
                "deletions": file_info["deletions"],
                "review": full_review,
            })
            files_summaries.append(f"【{file_info['filename']}】\n{full_review[:500]}")

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

        try:
            save_review(
                cache_key=cache_key,
                owner=info["owner"], repo=info["repo"],
                pr_number=info["pr_number"], head_sha=pr_info["head_sha"],
                pr_info=pr_info, file_reviews=file_reviews_for_cache, summary=full_summary,
            )
        except Exception as e:
            print(f"⚠️ 缓存保存失败: {e}")

        yield sse_event("done", {"from_cache": False, "cache_key": cache_key})

    return StreamingResponse(stream(), media_type="text/event-stream")


# ===================== API: 历史列表 =====================
@app.get("/history")
def history():
    """返回历史 PR 审查列表（JSON）"""
    return list_cached_reviews(limit=50)


# 🆕 ===================== API: 历史详情 =====================
@app.get("/history/{cache_key:path}")
def history_detail(cache_key: str):
    """🆕 按 cache_key 取一条完整审查结果（用于前端一次性渲染）"""
    cached = get_cached_review(cache_key)
    if not cached:
        raise HTTPException(404, "审查记录不存在")
    return cached


# ===================== 前端 =====================
@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_HTML


FRONTEND_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>PR Reviewer 🤖</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: #0d1117; color: #c9d1d9; height: 100vh; display: flex; }

/* ============ 左侧侧边栏 ============ */
.sidebar { width: 280px; background: #010409; border-right: 1px solid #30363d; display: flex; flex-direction: column; }
.sidebar-header { padding: 16px; border-bottom: 1px solid #30363d; }
.sidebar-header h2 { font-size: 14px; color: #8b949e; margin-bottom: 12px; }
.new-btn { width: 100%; padding: 8px; background: #238636; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; font-weight: 600; }
.new-btn:hover { background: #2ea043; }
.sidebar-list { flex: 1; overflow-y: auto; padding: 8px; }
.history-item { padding: 10px 12px; margin-bottom: 4px; border-radius: 6px; cursor: pointer; font-size: 12px; line-height: 1.5; border: 1px solid transparent; transition: all 0.15s; }
.history-item:hover { background: #161b22; border-color: #30363d; }
.history-item.active { background: #1f6feb20; border-color: #58a6ff; }
.history-item .title { color: #c9d1d9; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
.history-item .meta { color: #6e7681; font-size: 11px; }
.history-empty { text-align: center; color: #6e7681; font-size: 12px; padding: 24px; }

/* ============ 右侧主区 ============ */
.main { flex: 1; overflow-y: auto; padding: 20px; }
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

<!-- ============ 左侧侧边栏 ============ -->
<div class="sidebar">
    <div class="sidebar-header">
        <button class="new-btn" onclick="newReview()">＋ 新审查</button>
        <h2 style="margin-top:16px;">📚 历史审查</h2>
    </div>
    <div class="sidebar-list" id="historyList">
        <div class="history-empty">加载中...</div>
    </div>
</div>

<!-- ============ 右侧主区 ============ -->
<div class="main">
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
</div>

<script>
let currentFileDiv = null;
let currentSummaryDiv = null;
let currentCacheKey = null;

// ============ 加载历史列表 ============
async function loadHistory() {
    try {
        const res = await fetch("/history");
        const items = await res.json();
        const list = document.getElementById("historyList");
        if (items.length === 0) {
            list.innerHTML = '<div class="history-empty">还没有审查记录<br>从上方输入 PR 链接开始</div>';
            return;
        }
        list.innerHTML = items.map(item => `
            <div class="history-item ${item.cache_key === currentCacheKey ? 'active' : ''}" 
                 data-key="${item.cache_key}" onclick="loadHistoryDetail('${encodeURIComponent(item.cache_key)}')">
                <div class="title">${escapeHtml(item.title)}</div>
                <div class="meta">${item.owner}/${item.repo} #${item.pr_number} · ${item.head_sha}</div>
            </div>
        `).join("");
    } catch (e) {
        document.getElementById("historyList").innerHTML = 
            '<div class="history-empty">加载失败</div>';
    }
}

// ============ 点击历史项：一次性渲染 ============
async function loadHistoryDetail(cacheKey) {
    currentCacheKey = cacheKey;
    document.querySelectorAll(".history-item").forEach(el => {
        el.classList.toggle("active", el.dataset.key === cacheKey);
    });
    
    const output = document.getElementById("output");
    output.innerHTML = '<div class="status">⏳ 加载历史审查...</div>';
    
    try {
        const res = await fetch(`/history/${cacheKey}`);
        if (!res.ok) throw new Error("加载失败");
        const data = await res.json();
        renderFullReview(data);
    } catch (e) {
        output.innerHTML = `<div class="status" style="border-left-color:#f85149;">❌ ${e.message}</div>`;
    }
}

// ============ 一次性渲染完整审查 ============
function renderFullReview(data) {
    const output = document.getElementById("output");
    const pr = data.pr_info;
    
    let html = `
        <div class="status cache">⚡ 这是历史记录（缓存时间：${data.cached_at}）</div>
        <div class="pr-card">
            <h2>📌 ${escapeHtml(pr.title)}</h2>
            <div class="meta">
                👤 ${pr.author} · 📊 +${pr.additions}/-${pr.deletions} · 📁 ${pr.changed_files} 文件
                · <a href="${pr.url}" target="_blank" style="color:#58a6ff;">在 GitHub 查看 ↗</a>
            </div>
        </div>
    `;
    
    data.file_reviews.forEach((fr, idx) => {
        html += `
            <div class="file-review">
                <div class="filename">📄 [${idx + 1}/${data.file_reviews.length}] ${escapeHtml(fr.filename)}</div>
                <div class="stats">+${fr.additions || 0} / -${fr.deletions || 0}</div>
                <div class="content">${escapeHtml(fr.review)}</div>
            </div>
        `;
    });
    
    html += `
        <div class="summary">
            <h2>🎯 整体审查总结</h2>
            <div class="content">${escapeHtml(data.summary)}</div>
        </div>
    `;
    
    output.innerHTML = html;
    window.scrollTo(0, 0);
}

// ============ 新审查（清空主区）============
function newReview() {
    currentCacheKey = null;
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    document.getElementById("output").innerHTML = "";
    document.getElementById("prUrl").value = "";
    document.getElementById("prUrl").focus();
}

// ============ 流式审查（原逻辑保留）============
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
    currentCacheKey = null;
    document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
    
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
                handle(type, JSON.parse(data));
            }
        }
    } catch (e) {
        alert("出错: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "🚀 审查";
        loadHistory();  // 🆕 审查完刷新历史列表
    }
}

function handle(type, obj) {
    const output = document.getElementById("output");
    if (type === "status") {
        const d = document.createElement("div");
        d.className = "status" + (obj.message.includes("缓存") ? " cache" : "");
        d.textContent = obj.message;
        output.appendChild(d);
    } else if (type === "pr_info") {
        const d = document.createElement("div");
        d.className = "pr-card";
        d.innerHTML = `<h2>📌 ${escapeHtml(obj.title)}</h2>
            <div class="meta">👤 ${obj.author} · 📊 +${obj.additions}/-${obj.deletions} · 📁 ${obj.changed_files} 文件
            · <a href="${obj.url}" target="_blank" style="color:#58a6ff;">在 GitHub 查看 ↗</a></div>`;
        output.appendChild(d);
    } else if (type === "error") {
        const d = document.createElement("div");
        d.className = "status";
        d.style.borderLeftColor = "#f85149";
        d.textContent = "❌ " + obj.message;
        output.appendChild(d);
    } else if (type === "file_start") {
        currentFileDiv = document.createElement("div");
        currentFileDiv.className = "file-review";
        currentFileDiv.innerHTML = `<div class="filename">📄 [${obj.index}/${obj.total}] ${escapeHtml(obj.filename)}</div>
            <div class="stats">+${obj.additions} / -${obj.deletions}</div>
            <div class="content"></div>`;
        output.appendChild(currentFileDiv);
    } else if (type === "file_stream" && currentFileDiv) {
        currentFileDiv.querySelector(".content").textContent += obj.content;
        document.querySelector(".main").scrollTop = document.querySelector(".main").scrollHeight;
    } else if (type === "summary_start") {
        currentSummaryDiv = document.createElement("div");
        currentSummaryDiv.className = "summary";
        currentSummaryDiv.innerHTML = `<h2>🎯 整体审查总结</h2><div class="content"></div>`;
        output.appendChild(currentSummaryDiv);
    } else if (type === "summary_stream" && currentSummaryDiv) {
        currentSummaryDiv.querySelector(".content").textContent += obj.content;
        document.querySelector(".main").scrollTop = document.querySelector(".main").scrollHeight;
    } else if (type === "done") {
        currentCacheKey = obj.cache_key;
        const d = document.createElement("div");
        d.className = "status";
        d.style.borderLeftColor = "#3fb950";
        d.textContent = obj.from_cache ? "✅ 审查完成（来自缓存 ⚡）" : "✅ 审查完成（新鲜出炉 🔥）";
        output.appendChild(d);
    }
}

// ============ 工具：HTML 转义（防 XSS）============
function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// ============ 启动 ============
loadHistory();
</script>
</body>
</html>
"""