# 🧠 StudyBuddy — 你的 AI 学习陪伴 Agent

> 一个**主动追着你复习**的 AI 学习助手。会提取知识点、按艾宾浩斯曲线安排复习、智能出题、根据语义相似度生成融合题。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B6B)](https://www.trychroma.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-blueviolet)](https://www.deepseek.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## ✨ 一句话介绍

**告诉它你今天学了什么，它会变成你脑子里那个"30 天后还能提醒你复习"的小教练。**

---

## 📸 截图

![dashboard](docs/screenshot_ui.png)

> 主界面：左侧学习画像 + 语义搜索 + 同步向量；右侧今日复习题（支持关联式出题）

---

## 🎯 它解决什么问题

| 痛点 | StudyBuddy 怎么解决 |
|------|------|
| 学过就忘 | **艾宾浩斯遗忘曲线**自动调度复习时间 |
| 复习靠手动整理笔记 | **LLM 自动从对话里提取知识点**入库 |
| 复习题千篇一律 | **基于向量相似度生成"融合式应用题"** |
| 不知道自己学到哪了 | **学习画像 API** 看主题/掌握度/连续天数 |

---

## 🏗️ 技术架构

**FastAPI Web 层**（`/learn` `/due` `/answer` `/profile` `/search` `/ui`）  
　　⬇️  
**双数据库设计**：
- **SQLite + SQLAlchemy ORM** —— 存知识点、复习状态、掌握度
- **ChromaDB + sentence-transformers** —— 存向量，支持语义检索  

　　⬇️  
**DeepSeek LLM 层**：
- 知识点提取
- 智能出题
- 关联式融合题
- 智能判分

---

## 🛠️ 技术栈亮点

- **🧠 LLM 应用层**：Prompt 工程 + JSON Mode 强约束输出 + 失败自动降级
- **🔍 RAG / 向量检索**：ChromaDB + multilingual MiniLM，支持"语义相似题"生成
- **🗄️ 数据持久化**：SQLAlchemy ORM + SQLite，复习状态完整追踪
- **⚡ 异步设计**：知识点入库后**后台线程异步向量化**，不阻塞 API 响应
- **🎨 端到端可用**：纯单文件 HTML 单页前端，开箱即用，不依赖 npm

---

## 🚀 快速开始

克隆仓库：

    git clone https://github.com/Hackingburg/llm-learning-journey.git
    cd llm-learning-journey

安装依赖：

    pip install -r requirements.txt

配置 LLM API Key（在项目根目录创建 `.env`）：

    echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env

启动服务：

    uvicorn apps.study_buddy.main:app --reload --port 8003

打开浏览器：

- 交互式 UI: <http://localhost:8003/ui>
- FastAPI 自动文档: <http://localhost:8003/docs>

---

## 📚 核心 API

| Endpoint | 方法 | 说明 |
|----------|------|------|
| `/learn` | POST | 把"今天学了什么"喂给它 → 自动提取知识点入库 + 向量化 |
| `/due` | GET | 拿今天该复习的知识点 + AI 出题（支持 `?associated=true` 关联式出题）|
| `/answer` | POST | 提交回答 → AI 判分 → 自动更新掌握度 + 下次复习时间 |
| `/profile` | GET | 学习画像：主题分布、掌握度、连续学习天数 |
| `/search` | GET | 语义搜索知识点（基于向量相似度）|
| `/sync_vectors` | POST | 把数据库未向量化的知识点同步到 ChromaDB |
| `/ui` | GET | 单页交互界面 |

---

## 🎨 设计亮点

**1. 艾宾浩斯曲线复习调度**

复习间隔按 [1, 3, 7, 15, 30] 天递增；答对进入下一档，答错退回上一档，让"难记的"被更多次复习。

**2. 关联式出题（向量检索 + LLM 融合）**

用主知识点找向量库里语义最相近的 5 个知识点，让 LLM 把它们融合成一道应用题。失败时自动降级到普通题，用户永远不会被卡住。

**3. 后台异步向量化**

`/learn` 接口立刻返回响应，向量化放到后台线程执行，不阻塞用户体验。

---

## 🗂️ 项目结构

    apps/study_buddy/
    ├── models.py        # SQLAlchemy 数据模型 + 复习状态
    ├── extractor.py     # LLM 知识点提取 + 异步向量化
    ├── reviewer.py      # 艾宾浩斯复习调度
    ├── quiz.py          # 出题 + 关联式出题 + 智能判分
    ├── profile.py       # 学习画像聚合
    ├── vectorstore.py   # ChromaDB 向量库封装
    └── main.py          # FastAPI 路由 + 单页 UI

---

## 🌱 这是怎么来的

这是我在 [llm-learning-journey](../../README.md) —— **"从 0 到 LLM 应用工程师"** 学习路径中的项目之一。

期间还做过：

- 🤖 **PR Reviewer** — 自动审查 GitHub Pull Request 并发表评论
- 📄 **ResumeAI** — 简历优化助手
- 💬 **DeepChat / RoleAI** — 多角色对话助手

---

## 📜 License

MIT © 2026 [Hackingburg](https://github.com/Hackingburg)

---

> 💡 如果这个项目对你有启发，欢迎 ⭐ Star 或者 fork 改造成你自己的学习工具！