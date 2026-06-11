# PR Reviewer 🤖

> Week 6 业务应用：让 AI 当你的 PR 审查员

## ✨ 功能
- 解析任何公开 GitHub PR
- AI 逐文件流式审查 + 整体总结
- **结果缓存**：同一 commit 不重复花钱
- **错误重试**：LLM 抽风自动重试
- **GitHub Token**：5000/h API 限额

## 🚀 启动
```bash
uvicorn apps.pr_reviewer.main:app --reload --port 8002
```

## 📁 文件说明
- `github_client.py` - GitHub API 客户端
- `reviewer.py` - LLM 审查核心 Prompt
- `retry.py` - 重试装饰器（指数退避）
- `cache.py` - SQLite 结果缓存
- `main.py` - FastAPI Web 服务

## 🔑 环境变量
```bash
DEEPSEEK_API_KEY=sk-xxx     # 必须
GITHUB_TOKEN=ghp_xxx        # 可选，没有限流到 60/h
```