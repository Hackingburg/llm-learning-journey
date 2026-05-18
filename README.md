# 🚀 LLM Learning Journey

> 一个 Python 入门者向大模型应用工程师转型的真实记录

## 🌐 在线 Demo

**DeepChat API 已部署上线**：https://deepchat-nh50.onrender.com/docs

直接在浏览器里就可以体验 AI 对话、查看 OpenAPI 文档。

## ⭐ 主要作品

### DeepChat - 命令行 AI 助手
独立开发的产品级 ChatBot，整合 LLM 应用核心能力：
- 💬 流式输出（打字机效果）
- 🧠 多轮对话记忆
- 📏 滑动窗口管理（防止上下文超限）
- 💰 实时 Token 与成本追踪
- 💾 SQLite 持久化（重启不丢数据）
- 🌐 FastAPI Web 服务 + Docker 容器化
- ☁️ 已部署到 Render 云端

➡️ [核心代码](./day08_deepchat_db.py)

## 📖 关于这个仓库

这里记录我从 0 开始学习大模型应用开发的全过程，包括代码、笔记、踩过的坑和做过的项目。

## 🎯 学习目标

- ✅ 掌握 LLM API 调用与 Prompt 工程
- 🔄 构建 RAG 知识库问答系统
- 🔄 开发 AI Agent 智能体
- 🔄 学习模型微调（LoRA）
- 🔄 成为一名 LLM 应用工程师

## 📅 学习进度

| Day | 日期 | 内容 | 状态 |
|-----|------|------|------|
| 01 | 2026-05-04 | 第一次调用 DeepSeek API | ✅ |
| 02 | 2026-05-05 | Pydantic + 多轮对话 ChatBot | ✅ |
| 03 | 2026-05-06 | 流式输出 + Token统计 | ✅ |
| 04 | 2026-05-07 | DeepChat 产品级 ChatBot 🎁 | ✅ |
| 05 | 2026-05-11 | 学习 Prompt 工程四大基本法 | ✅ |
| 06 | 2026-05-12 | 让 AI 输出严格符合业务规范的 JSON | ✅ |
| 07 | 2026-05-13 | 用 FastAPI 把 Deepchat Web 服务化 | ✅ |
| 08 | 2026-05-14 | Deepchat 持久化 | ✅ |
| 09 | 2026-05-18 | 将 Deepchat 上线到 Render | ✅ |


## 🛠️ 技术栈

- **语言**: Python 3.12
- **LLM**: DeepSeek
- **核心库**: requests, httpx, pydantic, python-dotenv

## 📂 项目结构

```
llm-learning-journey/
├── day01_first_call.py         # Day 1: 第一次 API 调用
├── day02_pydantic_basics.py    # Day 2: Pydantic 基础
├── day02_chat_with_memory.py   # Day 2: 带记忆的 ChatBot
├── day03_streaming.py          # Day 3: 流式输出
├── day03_token_count.py        # Day 3: Token 成本计算
├── day04_deepchat.py           # Day 4: 产品级 ChatBot ”Deepchat“
├── day05_prompt_egineering.py  # Day 5: Prompt 工程四大基本法
├── day05_my_experiment.py      # Day 5: 角色扮演小实验
├── day06_json_basic.py         # Day 6: 靠 prompt 让 AI 输出 JSON 格式的文本
├── day06_json_mode.py          # Day 6: 强制让 AI 只输出 JSON 格式
├── day06_pydantic_extract.py   # Day 6: 工业级结构化输出
├── day07_ai_api.py             # Day 7: 把 AI 能力变成 Web API
├── day07_deepchat_api.py       # Day 7: DeepChat Web 服务化
├── day07_fastapi_hello.py      # Day 7: FastAPI 入门
├── day08_deepchat_db.py        # Day 8: DeepChat 持久化版
├── day08_sqlalchemy_basics.py  # Day 8: SQLAlchemy 入门
├── day08_sqlite_basics.py      # Day 8: sqlite 入门
├── Dockerfile                  # Day 9: 镜像
├── .dockerignore               # Day 9: 镜像忽略文件
├── .env.example
├── .gitignore
├── requirements.txt
├── LEARNING_LOG.md
└── README.md
```

## 🔧 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Hackingburg/llm-learning-journey.git
cd llm-learning-journey

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Key
cp .env.example .env
# 编辑 .env 填入你的 DEEPSEEK_API_KEY

# 5. 运行
python day01_first_call.py
```
