# 📄 ResumeAI — 让 AI 帮你把简历改到能投出去

> 上传你的简历 → AI 逐条挑刺 → 给出具体修改建议 → 看完照着改就能用。专治"简历投了几十份没回音"的尴尬。

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek-blueviolet)](https://www.deepseek.com/)
[![Markdown](https://img.shields.io/badge/Format-Markdown-000000?logo=markdown)](https://www.markdownguide.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](../../LICENSE)

---

## ✨ 一句话介绍

把你的简历喂给它 —— 它会像一个挑剔但温柔的招聘经理一样，一条条告诉你"这里写得不够好，应该改成 XX"。

---

## 📸 截图

![resume_ai_ui](https://github.com/Hackingburg/llm-learning-journey/raw/main/docs/screenshot_resume_ai.png)

> 主界面：左侧上传/粘贴简历 → 右侧 AI 分析报告（结构 / 内容 / 表达 三维度建议）

---

## 🎯 它解决什么问题

| 痛点 | ResumeAI 怎么解决 |
|------|------|
| 简历投了很多没回音，不知道哪里有问题 | LLM 从招聘视角逐条挑刺 |
| 不知道自己的描述是"自夸"还是"客观" | AI 标出"含金量过低"和"缺乏数据支撑"的句子 |
| 简历格式凌乱 | 解析后按结构化维度给建议 |
| 不知道该用什么动词 / 怎么量化成果 | AI 直接给出可复制的改写示例 |

---

## 🏗️ 技术架构

前端层：单页 HTML，支持文件上传 + 文本粘贴两种输入

⬇️

FastAPI Web 层：`/analyze`、`/upload`、`/ui`

⬇️

Core 业务层：

- **Parser** — 简历文件解析（Markdown / 纯文本，可扩展 PDF）
- **Analyzer** — LLM 多维度评估 + 改写建议生成
- **Prompt 工程** — 引导 LLM 按"结构 / 内容 / 表达"三维度输出结构化报告

⬇️

DeepSeek LLM —— 简历分析与建议生成

---

## 🛠️ 技术栈亮点

- **📤 双输入方式** — 支持文件上传 + 文本粘贴，覆盖不同用户习惯
- **🎯 多维度评估** — 不是"夸一通"，而是按 结构 / 内容 / 表达 分维度打分
- **✍️ 给出"可复制的改写"** — 不只指出问题，还告诉你"应该改成这样"
- **🚀 端到端可用** — 配上自带的 sample_resume.md，开箱可体验
- **🎨 单文件前端** — 不依赖 npm，纯 HTML + Fetch API

---

## 🚀 快速开始

克隆仓库：

    git clone https://github.com/Hackingburg/llm-learning-journey.git
    cd llm-learning-journey

安装依赖：

    pip install -r requirements.txt

配置 API Key（在项目根目录创建 .env）：

    DEEPSEEK_API_KEY=sk-your-deepseek-key

启动服务：

    uvicorn apps.resume_ai.main:app --reload --port 8001

打开浏览器：

- 交互式 UI: <http://localhost:8001/ui>
- FastAPI 自动文档: <http://localhost:8001/docs>

体验技巧：第一次用可以直接拿仓库里的 `sample_resume.md` 试试效果。

---

## 📚 核心 API

| Endpoint | 方法 | 说明 |
|----------|------|------|
| `/analyze` | POST | 传入简历文本，返回结构化分析报告 |
| `/upload` | POST | 上传简历文件，解析后自动分析 |
| `/ui` | GET | 单页交互界面 |

---

## 🎨 设计亮点

**1. 不是"夸夸 AI"，是"挑刺 AI"**

很多简历工具会让 AI 写一堆漂亮话。这个工具反过来 —— 让 AI 站在招聘者视角，专门指出**哪里写得不够好、为什么不够好、应该怎么改**。

**2. 三维度评估框架**

- **结构** —— 模块完整性、顺序合理性、信息层级
- **内容** —— 描述具体性、成果可量化、技能匹配度
- **表达** —— 动词使用、句式干练度、专业术语恰当性

每个维度独立给建议，避免"一锅烩"的模糊反馈。

**3. 可复制的改写示例**

对每条建议，AI 都会给出**"原文 → 建议改成"** 的对照，用户直接复制粘贴就能用，零思考成本。

**4. 自带 sample 体验**

仓库里附了一份 `sample_resume.md` —— 新用户不用准备自己的简历也能立刻体验产品。

---

## 🗂️ 项目结构

    apps/resume_ai/
    ├── main.py             # FastAPI 路由 + 文件上传 + UI
    ├── parser.py           # 简历文件解析（Markdown / 文本）
    ├── analyzer.py         # LLM 多维度分析 + 建议生成
    └── sample_resume.md    # 自带的示例简历（开箱体验用）

---

## 🌱 这是怎么来的

这是我在 [llm-learning-journey](../../README.md) —— "从 0 到 LLM 应用工程师" 学习路径中的项目之一。

期间还做过：

- 🧠 [StudyBuddy](../study_buddy/) — AI 学习陪伴 Agent（艾宾浩斯 + RAG + 关联式出题）
- 🤖 [PR Reviewer](../pr_reviewer/) — GitHub PR 智能审查工具（SSE 流式 + 缓存 + 重试）
- 💬 DeepChat / RoleAI — 多角色对话助手

---

## 📜 License

MIT © 2026 [Hackingburg](https://github.com/Hackingburg)

---

> 💡 写简历的时候欢迎试试它。觉得有用的话欢迎 ⭐ Star，有问题欢迎提 Issue。