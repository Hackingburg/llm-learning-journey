# ResumeAI 📝 - AI 简历优化助手

> Week 5 业务应用项目：用 LLM 帮人优化简历

## ✨ 核心功能
- 上传简历（.txt / .md）
- 输入目标岗位
- AI 三步分析：解读 → 匹配 → 修改建议
- 流式输出 AI 思考过程

## 🛠️ 技术栈
- FastAPI + DeepSeek + 流式 SSE
- 复用 Day 1-16 所有所学

## 🚀 启动
```bash
uvicorn apps.resume_ai.main:app --reload --port 8001
```