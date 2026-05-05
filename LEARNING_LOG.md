# 📝 学习日志

## Day 1 - 2026-05-04（周一）

### 🎯 今日目标
- 配置 Python 3.12 开发环境
- 跑通第一个 DeepSeek API 调用
- 上传到 GitHub

### ✅ 完成情况
- [x] 升级 Python 3.9 → 3.12（解决了 .zshrc 权限问题）
- [x] 创建虚拟环境，养成隔离环境的好习惯
- [x] 调通 DeepSeek API，理解 system/user/messages 结构
- [x] 学会用 .env 管理 API Key（安全意识 +1）
- [x] 推送到 GitHub

### 💡 关键收获
- 所有 LLM 应用的核心结构：**输入 → 构造 messages → API → 解析响应**
- temperature 参数：代码任务用低值，创意任务用高值
- API Key 绝不能写进代码或推到 GitHub

### 🐛 踩过的坑
- `brew upgrade` 不会自动升级 Python 主版本
- `.zshrc` 文件权限被改导致写入失败，用 `sudo chown` 修复

### 📌 明日计划
- 学习 Pydantic：用结构化数据定义请求和响应
- 实现多轮对话（带历史记录管理）

## Day 2 -2026-05-05（周二）

### 🎯 今日目标
- 学习 Pydantic 数据模型
- 实现带记忆的多轮对话 ChatBot

### ✅ 完成情况
- [x] Pydantic 基础：BaseModel、Field、Literal、自动校验
- [x] 理解 LLM 的“无状态”本质
- [x] 用类封装ChatBot， 维护 messages 历史
- [x] 实现命令行交互（exit/reset/history）

### 💡 关键收获 
- **LLM 是无状态的**， “记忆”靠每次把完整历史塞进messages
- Pydantic 的价值： 自动校验 + IDE 补全 + 数据契约
- 'model_dump()' 把 Pydantic 对象转字典， 发 API 必备
- 给 requests 加 ‘timeout’ 是工程化的基本素养

### 📌 明日计划
- 实现“流式输出” （打字机效果， 体验更好）
- 给 ChatBot 加上 token 计数和成本统计
