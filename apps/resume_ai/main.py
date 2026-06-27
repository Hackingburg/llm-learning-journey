"""
ResumeAI - Web 服务
🎯 完整的简历优化助手 Web 应用
"""
import json
import anyio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from .parser import parse_resume
from .analyzer import analyze_resume


app = FastAPI(title="ResumeAI 📝")


def sse_event(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    target_position: str = Form(...),
):
    """⭐ 上传简历 + 岗位 → 流式分析"""
    if not file.filename.endswith((".txt", ".md")):
        raise HTTPException(400, "暂时只支持 .txt 和 .md 文件")
    
    try:
        content = (await file.read()).decode("utf-8")
    finally:
        await file.close()
    
    # 解析简历
    try:
        parsed = parse_resume(content, file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e))
    
    # 流式分析
    async def stream():
        yield sse_event("parsed", {
            "word_count": parsed["word_count"],
            "sections": list(parsed["sections"].keys()),
        })
        
        gen = analyze_resume(parsed["raw_text"], target_position)
        while True:
            event = await anyio.to_thread.run_sync(next, gen, None)
            if event is None:
                break
            yield sse_event(event.get("type", "unknown"), event)
    
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/ui", response_class=HTMLResponse)
def index():
    return FRONTEND_HTML


FRONTEND_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ResumeAI 📝</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "PingFang SC", sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
.container { max-width: 900px; margin: 0 auto; background: #fff; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); overflow: hidden; }
.header { background: #1e293b; color: #fff; padding: 30px 40px; }
.header h1 { font-size: 28px; margin-bottom: 8px; }
.header p { color: #94a3b8; }
.form { padding: 30px 40px; }
.field { margin-bottom: 20px; }
.field label { display: block; font-weight: 600; margin-bottom: 8px; color: #334155; }
.field input[type=file], .field textarea { width: 100%; padding: 12px; border: 2px dashed #cbd5e1; border-radius: 8px; font-size: 14px; font-family: inherit; }
.field textarea { min-height: 80px; resize: vertical; }
button { width: 100%; padding: 14px; background: #6366f1; color: #fff; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
button:disabled { background: #94a3b8; cursor: not-allowed; }
button:hover:not(:disabled) { background: #4f46e5; }
.results { padding: 30px 40px; }
.step { margin-bottom: 25px; padding: 20px; background: #f8fafc; border-left: 4px solid #6366f1; border-radius: 4px; }
.step h3 { color: #1e293b; margin-bottom: 12px; }
.step .content { white-space: pre-wrap; line-height: 1.7; color: #334155; }
.parsed-info { background: #ecfdf5; padding: 12px; border-radius: 6px; margin-bottom: 20px; color: #047857; font-size: 14px; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📝 ResumeAI - AI 简历优化助手</h1>
        <p>上传简历 + 目标岗位 → AI 三步分析 + 给出具体修改建议</p>
    </div>
    
    <div class="form">
        <div class="field">
            <label>📄 上传简历（.txt 或 .md）</label>
            <input type="file" id="resume" accept=".txt,.md" />
        </div>
        <div class="field">
            <label>🎯 目标岗位描述</label>
            <textarea id="job" placeholder="例如：高级 Python 工程师，要求 3 年以上经验，熟悉 FastAPI、Docker..."></textarea>
        </div>
        <button id="analyzeBtn" onclick="analyze()">🚀 开始分析</button>
    </div>
    
    <div class="results" id="results"></div>
</div>

<script>
async function analyze() {
    const file = document.getElementById("resume").files[0];
    const job = document.getElementById("job").value.trim();
    const btn = document.getElementById("analyzeBtn");
    const results = document.getElementById("results");
    
    if (!file) { alert("请上传简历"); return; }
    if (!job) { alert("请填写目标岗位"); return; }
    
    btn.disabled = true;
    btn.textContent = "分析中...";
    results.innerHTML = "";
    
    const fd = new FormData();
    fd.append("file", file);
    fd.append("target_position", job);
    
    let currentStepDiv = null;
    
    try {
        const res = await fetch("/analyze", {method: "POST", body: fd});
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
                
                if (type === "parsed") {
                    const info = document.createElement("div");
                    info.className = "parsed-info";
                    info.textContent = `✅ 解析成功：${obj.word_count} 字 / ${obj.sections.length} 个章节`;
                    results.appendChild(info);
                }
                else if (type === "start") {
                    currentStepDiv = document.createElement("div");
                    currentStepDiv.className = "step";
                    currentStepDiv.innerHTML = `<h3>${obj.title}</h3><div class="content"></div>`;
                    results.appendChild(currentStepDiv);
                }
                else if (type === "stream" && currentStepDiv) {
                    currentStepDiv.querySelector(".content").textContent += obj.content;
                    window.scrollTo(0, document.body.scrollHeight);
                }
            }
        }
    } catch (e) {
        alert("出错了: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "🚀 开始分析";
    }
}
</script>
</body>
</html>
"""