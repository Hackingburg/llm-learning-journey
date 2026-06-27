# 🤖 PR Reviewer — 让 GitHub PR 拥有 24/7 在线的智能审查员

> 一个自动审查 GitHub Pull Request 的 AI 工具。读懂代码改动 → 给出有理有据的建议 → 一键发布到 PR 评论区。SSE 流式输出 + 结果缓存 + 失败重试，工程级实现。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SSE](https://img.shields.io/badge/Stream-SSE-orange)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
[![GitHub API](https://img.shields.io/badge/GitHub-REST_API-181717?logo=github&logoColor=white)](https://docs.github.com/en/rest)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-blueviolet)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](../../LICENSE)

---

## ✨ 一句话介绍

贴一个 GitHub PR 链接进来 —— 它会像一个资深 reviewer 一样，逐字流式输出审查意见，并能一键把评论发到 PR 下面。

---

## 📸 截图

![pr_reviewer_ui](https://github.com/Hackingburg/llm-learning-journey/raw/main/docs/screenshot_pr_reviewer.png)

> 主界面：左侧粘贴 PR 链接 → 右侧 SSE 实时流式输出审查意见

---

## 🎯 它解决什么问题

| 痛点 | PR Reviewer 怎么解决 |
|------|------|
| 团队太小，没人能给我 review 代码 | AI 当你的 24/7 在线 reviewer |
| 大 PR 没人愿意细看 | AI 不嫌长，逐文件逐 diff 给出建议 |
| Review 等好几天才回 | 几秒钟开始流式输出，不用等 |
| 同一个 PR 反复看，浪费 LLM 额度 | 结果缓存，同一 PR 只算一次 |
| 网络抖动 / LLM 偶发 5xx | 自动指数退避重试，不中断流程 |

---

## 🏗️ 技术架构

前端层：单页 HTML + EventSource（SSE 客户端）

⬇️

FastAPI Web 层：`/review/stream`、`/review/publish`、`/history`、`/ui`

⬇️

Core 业务层：

- **GitHub Client** — 拉取 PR diff、文件、元数据；发布审查评论
- **Reviewer** — 构造 Prompt，调用 LLM，流式产出审查意见
- **Cache** — 基于 PR + commit SHA 做结果缓存，避免重复花 token
- **Retry** — 指数退避重试，处理网络抖动与 LLM 偶发错误
- **Formatter** — 把 LLM 原始输出格式化成 Markdown 评论

⬇️

DeepSeek LLM —— Code Review 推理

---

## 🛠️ 技术栈亮点

- **🌊 SSE 流式输出** — 用户体验远超"转圈等几十秒"的同步接口
- **💾 双层缓存策略** — 按 PR + commit SHA 缓存，节省 LLM 成本
- **🔁 指数退避重试** — 工程级容错，应对网络与服务端抖动
- **🤖 GitHub API 闭环** — 不止"审查"，还能直接发布评论到 PR
- **📜 历史追溯** — 记录每次审查，可回看
- **🎨 单文件前端** — 不依赖 npm，开箱即用

---

## 🚀 快速开始

克隆仓库：

    git clone https://github.com/Hackingburg/llm-learning-journey.git
    cd llm-learning-journey

安装依赖：

    pip install -r requirements.txt

配置 API Key（在项目根目录创建 .env）：

    DEEPSEEK_API_KEY=sk-your-deepseek-key
    GITHUB_TOKEN=ghp_your-github-token

启动服务：

    uvicorn apps.pr_reviewer.main:app --reload --port 8002

打开浏览器：

- 交互式 UI: <http://localhost:8002/ui>
- FastAPI 自动文档: <http://localhost:8002/docs>

---

## 📚 核心 API

| Endpoint | 方法 | 说明 |
|----------|------|------|
| `/review/stream` | GET | 传入 PR URL，SSE 流式返回审查意见 |
| `/review/publish` | POST | 把生成好的审查意见发布到 GitHub PR 评论区 |
| `/history` | GET | 查看历史审查记录 |
| `/cache/clear` | POST | 清空指定 PR 的缓存（强制重新审查） |
| `/ui` | GET | 单页交互界面 |

---

## 🎨 设计亮点

**1. SSE 流式审查 — 让等待变成"陪伴感"**

不是"提交 → 等 30 秒 → 一坨结果砸出来"，而是 LLM 边写边吐字，用户立刻看到反馈，体验差异巨大。

**2. 基于 commit SHA 的缓存键设计**

缓存键设计：`cache_key = sha256(pr_url + commit_sha)`

只要 PR 没有新 push，就直接命中缓存。一次审查只算一次 LLM 钱。

**3. 指数退避重试（Exponential Backoff）**

- 失败第 1 次：等 1 秒重试
- 失败第 2 次：等 2 秒重试
- 失败第 3 次：等 4 秒重试

应对真实生产环境中的网络与 LLM 服务波动，不让流程中断。

**4. 审查闭环 — 不止"看"，还能"发"**

很多 AI 代码审查工具只能"展示"结果。这个工具调用 GitHub API，把审查直接发布到 PR 评论区 —— 真正集成进开发工作流。

---

## 🗂️ 项目结构

    apps/pr_reviewer/
    ├── main.py             # FastAPI 路由 + SSE 流式接口 + UI
    ├── reviewer.py         # LLM 审查核心逻辑 + Prompt 工程
    ├── github_client.py    # GitHub API 封装（拉 PR、发评论）
    ├── cache.py            # 审查结果缓存层
    ├── retry.py            # 指数退避重试机制
    └── formatter.py        # 输出格式化为 Markdown

---

## 🌱 这是怎么来的

这是我在 [llm-learning-journey](../../README.md) —— "从 0 到 LLM 应用工程师" 学习路径中的项目之一。

期间还做过：

- 🧠 [StudyBuddy](../study_buddy/) — AI 学习陪伴 Agent（艾宾浩斯 + RAG + 关联式出题）
- 📄 [ResumeAI](../resume_ai/) — 简历优化助手
- 💬 DeepChat / RoleAI — 多角色对话助手

---

## 📜 License

MIT © 2026 [Hackingburg](https://github.com/Hackingburg)

---

> 💡 觉得有用的话欢迎 ⭐ Star。Issue / PR 都欢迎，毕竟一个 PR Reviewer 项目，没 PR 怎么行？😄