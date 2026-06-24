"""
StudyBuddy - Web 服务（含 UI）
🎯 暴露核心 API，并提供交互式 /ui 页面（集成画像/搜索/复习/提交）
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from .extractor import extract_knowledge, save_knowledge_points
from .reviewer import get_due_knowledge_points, update_review_result, get_stats
from .quiz import generate_quiz, generate_associated_quiz, grade_answer
from .profile import build_user_profile
from .vectorstore import find_similar_points, sync_all_from_db
from .models import SessionLocal, KnowledgePoint

app = FastAPI(title="StudyBuddy 🧠")

class ChatRequest(BaseModel):
    message: str

class AnswerRequest(BaseModel):
    point_id: int
    question: str
    user_answer: str

@app.post("/learn")
def learn(req: ChatRequest):
    points = extract_knowledge(req.message)
    saved = save_knowledge_points(req.message, points)
    return {
        "extracted_count": len(saved),
        "points": [
            {"id": p.id, "topic": p.topic, "content": p.content, "difficulty": p.difficulty}
            for p in saved
        ],
    }

@app.get("/due")
def due(associated: bool = False):
    points = get_due_knowledge_points(limit=10)
    quizzes = []
    for p in points:
        if associated:
            related = find_similar_points(f"{p.topic}: {p.content}", top_k=5, exclude_ids=[p.id])
            assoc = generate_associated_quiz(p, related)
            if assoc and assoc.get("question"):
                quizzes.append({
                    "point_id": p.id,
                    "topic": p.topic,
                    "difficulty": p.difficulty,
                    "question": assoc["question"],
                    "rationale": assoc.get("rationale"),
                    "_correct_point": p.content,
                    "related": related,
                })
                continue
        q = generate_quiz(p)
        quizzes.append({
            "point_id": p.id,
            "topic": p.topic,
            "difficulty": p.difficulty,
            "question": q,
            "_correct_point": p.content,
            "related": [],
        })
    return {"total": len(quizzes), "quizzes": quizzes}

@app.post("/answer")
def answer(req: AnswerRequest):
    db = SessionLocal()
    try:
        point = db.query(KnowledgePoint).get(req.point_id)
        if not point:
            raise HTTPException(404, "知识点不存在")
        correct_point = point.content
    finally:
        db.close()

    result = grade_answer(req.question, correct_point, req.user_answer)
    updated = update_review_result(req.point_id, result["correct"])
    return {
        "correct": result["correct"],
        "feedback": result["feedback"],
        "new_mastery": updated.mastery,
        "next_review_at": updated.next_review_at.isoformat(),
    }

@app.get("/profile")
def profile():
    return build_user_profile()

@app.get("/stats")
def stats():
    return get_stats()

@app.get("/search")
def search(q: str, top_k: int = 5):
    results = find_similar_points(q, top_k=top_k)
    return {"query": q, "results": results}

@app.post("/sync_vectors")
def sync_vectors():
    return sync_all_from_db()

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return FRONTEND_UI

# Frontend UI (single-page)
FRONTEND_UI = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<title>StudyBuddy UI 🧠</title>
<style>
body { font-family: -apple-system, Roboto, "PingFang SC", sans-serif; margin:0; height:100vh; display:flex; background:#0f1724; color:#e6eef8;}
.sidebar { width:300px; padding:16px; background:#071025; border-right:1px solid #122033; overflow:auto; }
.main { flex:1; padding:20px; overflow:auto; }
.h { color:#7dd3fc; font-weight:700; margin-bottom:10px;}
.card { background:#071427; border:1px solid #123041; padding:12px; border-radius:8px; margin-bottom:12px;}
button { background:#06b6d4; border:none; color:#022; padding:8px 12px; border-radius:6px; cursor:pointer; }
input, textarea { width:100%; padding:8px; border-radius:6px; border:1px solid #1f3b4a; background:#02131b; color:#e6eef8;}
.small { font-size:13px; color:#98a8b8; }
.kp { margin-bottom:8px; padding:8px; border-radius:6px; background:#021520; border:1px solid #123c45; }
</style>
</head>
<body>
  <div class="sidebar">
    <div class="h">🧠 StudyBuddy</div>
    <div class="card">
      <div style="display:flex; gap:8px;">
        <input id="learnInput" placeholder="写一句：今天学了 X" />
        <button onclick="learn()">学</button>
      </div>
      <div style="margin-top:8px;" class="small">把一句学习话发送给系统，它会提取知识点并入库。</div>
    </div>

    <div class="card">
      <div class="h">📊 学习画像</div>
      <pre id="profile" style="white-space:pre-wrap; font-size:13px;"></pre>
      <button onclick="loadProfile()">刷新画像</button>
    </div>

    <div class="card">
      <div class="h">🔎 语义检索</div>
      <input id="q" placeholder="搜索相关知识点（语义搜索）" />
      <div style="display:flex; gap:8px; margin-top:8px;">
        <button onclick="search()">搜</button>
        <button onclick="syncVectors()">同步向量</button>
      </div>
      <div id="searchRes" style="margin-top:8px;"></div>
    </div>

    <div class="card">
      <div class="h">📅 本地测试工具</div>
      <div class="small">注意：/due 会调用 LLM 出题，可能要几秒</div>
      <label style="display:block; margin-top:8px;">
        <input id="assocToggle" type="checkbox" /> 关联式出题（尝试把相似知识点合并出题）
      </label>
      <button onclick="loadDue()">抓取今日复习</button>
    </div>
  </div>

  <div class="main">
    <div id="content">
      <h2 style="color:#7dd3fc">今日复习 / 出题</h2>
      <div id="dueArea"></div>
    </div>
  </div>

<script>
async function safeJson(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text.slice(0,200)}`);
  }
  return res.json();
}

async function loadProfile(){
  const res = await fetch('/profile');
  const data = await safeJson(res);
  document.getElementById('profile').textContent = JSON.stringify(data, null, 2);
}

async function learn(){
  const v = document.getElementById('learnInput').value.trim();
  if (!v) return alert('输入一句学习内容');
  const res = await fetch('/learn', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:v})});
  const j = await safeJson(res);
  alert('提取到: ' + j.extracted_count + ' 条');
  document.getElementById('learnInput').value='';
  loadProfile();
}

async function syncVectors(){
  const res = await fetch('/sync_vectors', {method:'POST'});
  const j = await safeJson(res);
  alert('同步结果: ' + JSON.stringify(j));
}

async function search(){
  const q = document.getElementById('q').value.trim();
  if (!q) return alert('输入关键词');
  const res = await fetch(`/search?q=${encodeURIComponent(q)}`);
  const j = await safeJson(res);
  const el = document.getElementById('searchRes');
  if (!j.results.length) el.innerHTML = '<div class="small">未找到相关知识点</div>';
  else {
    el.innerHTML = j.results.map(r=>`<div class="kp"><b>${r.topic}</b><div class="small">${r.content}</div><div class="small">相似度:${(r.similarity||0).toFixed(2)}</div></div>`).join('');
  }
}

async function loadDue(){
  const assoc = document.getElementById('assocToggle').checked;
  const res = await fetch('/due' + (assoc ? '?associated=true' : ''));
  const j = await safeJson(res);
  const area = document.getElementById('dueArea');
  area.innerHTML = '';
  if (!j.quizzes.length) {
    area.innerHTML = '<div class="small">今天没有到复习时间的知识点</div>';
    return;
  }
  j.quizzes.forEach(q => {
    const div = document.createElement('div');
    div.className = 'card';
    let relatedHtml = '';
    if (q.related && q.related.length) {
       relatedHtml = '<div class="small" style="margin-top:8px;"><b>相关知识点：</b>' +
         q.related.map(r => `<div>${r.topic}: ${r.content}</div>`).join('') + '</div>';
    }
    let rationaleHtml = q.rationale ? `<div class="small" style="margin-top:6px;"><b>出题理由：</b>${q.rationale}</div>` : '';
    div.innerHTML = `<div><b>${q.topic}</b> <span class="small">[${q.difficulty}]</span></div>
                     <div style="margin-top:8px;">${q.question}</div>
                     ${relatedHtml}
                     ${rationaleHtml}
                     <div style="margin-top:8px;"><input id="ans_${q.point_id}" placeholder="你的回答"/></div>
                     <div style="margin-top:8px;"><button onclick="submitAnswer(${q.point_id}, ${JSON.stringify(q.question).replace(/'/g, \"\\\\'\")})">提交回答</button></div>
                     <div id="fb_${q.point_id}" style="margin-top:8px;"></div>`;
    area.appendChild(div);
  });
}

async function submitAnswer(point_id, question){
  const val = document.getElementById('ans_'+point_id).value || '';
  const res = await fetch('/answer', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({point_id, question, user_answer: val})});
  const j = await safeJson(res);
  document.getElementById('fb_'+point_id).innerHTML = `<div class="small">${j.correct ? '✅ 正确' : '❌ 不正确'} — ${j.feedback} <br/> 新掌握度: ${(j.new_mastery*100).toFixed(0)}% 下次复习:${j.next_review_at}</div>`;
  loadProfile();
}
window.onload = loadProfile;
</script>
</body>
</html>
"""