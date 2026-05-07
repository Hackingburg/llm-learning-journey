# 🚀 LLM Learning Journey

> 一个 Python 入门者向大模型应用工程师转型的真实记录

## ⭐ 主要作品

### DeepChat - 命令行 AI 助手
独立开发的产品级 ChatBot，整合 LLM 应用核心能力：
- 💬 流式输出（打字机效果）
- 🧠 多轮对话记忆
- 📏 滑动窗口管理（防止上下文超限）
- 💰 实时 Token 与成本追踪
- 💾 会话持久化（JSON 存储）

➡️ [查看代码](./day04_deepchat.py)

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
