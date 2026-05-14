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

## Day 3 - 2026-05-06 (周三)

### 🎯 今日目标 
- 实现流式输出（打字机效果）
- 理解 Token 概念和成本计算

### ✅ 完成情况
- [x] 学会用 ‘steam=True’ 实现流式相应
- [x] 理解 SSE 协议 （Server-Sent Events）
- [x] 掌握 Token 概念， 会算 API 调用成本
- [x] 用 ’usage‘ 字段查看每次调用的token 消耗

### 💡 关键收获
- **流式 vs 普通**： 体验差距巨大， 所有 ChatBot 产品必须支持流式
- **Token 不等于字数**：中文 1 token ≈ 1-1.5 字
- **成本结构**： 输入便宜，输出贵（月4倍）， 所以 Prompt 要精炼
- **历史会无限增长** → 明天用滑动窗口/摘要解决

### 📌 明日计划
- 把流式输出 + Token 统计 整合进 ChatBot 类
- 实现“滑动窗口”历史管理（防止 token 超限和成本失控）

## Day 4 - 2026-05-07（周四）

### 🎯 今日目标
- 整合 Day 1-3 所学，打造产品级ChatBot “DeepChat”
- 实现滑动窗口，成本追踪，会话持久化

### ✅ 完成情况
- [x] 把流式输出、多轮记忆、Pydantic 全部整合
- [x] 实现滑动窗口（防止历史无限增长）
- [x] 实时追踪 token 与成本（流式也能拿 usage）
- [x] 会话保存 / 加载 （JSON 持久化）
- [x] 命令系统： /help /reset /history /stats /save /load /exit 

### 关键收获
- **配置集中化**：用config 类统一管理常量，远超魔法数学
- **流式响应 + usage**：要加 `stream_options： {"include_usage": True}`
- **滑动窗口**：保留最近 N 轮，平衡“记忆”与“成本”
- **持久化思维**：用pathlib 操作文件比 os.path 优雅得多
- **隐私意识**： 会话记录绝不能推 GitHub

### 📌 第一阶段总结（Week 1）
- 4 天完成从零调通 API → 产品级 ChatBot
- 已具备开发任何 LLM 应用的基础能力
- **下周计划**：Prompt 工程深入 + FastAPI 把 DeepChat 变成 Web 服务

## Day 5 - 2026-05-11（周一）

### 🎯 今日目标
- 学习 Prompt 工程四大基本法
- 通过对比实验亲眼看到效果差异

### ✅ 完成情况
- [x] 角色扮演：体验同一问题不同角色的回答风格
- [x] Few-shot：理解给例子对输出格式的巨大影响
- [x] CoT 思维链：见证"一步一步想"对推理题的提升
- [x] 温度调控：感受 0.1 vs 1.5 的输出差异
- [x] 「健身教练 vs 营养师」对比同一减脂问题的回答视角差异

### 💡 关键收获
- **Prompt 是 LLM 应用的灵魂**，同样的模型 prompt 不同效果天差地别
- **Few-shot > Zero-shot** 几乎在所有任务上都成立
- **CoT 不只是话术**，是让 AI 把"思考过程"作为中间产物输出，准确率会大幅提升
- **温度选择**：稳定/事实类用低温，创意/发散用高温

### 🐛 踩过的坑
- 还是会拼错一些单词

### 📌 明日计划
- 学习"结构化输出"：让 AI 返回严格的 JSON
- 用 Pydantic 校验 LLM 的输出（业务必备）

## Day 6 - 2026-05-12（周二）

### 🎯 今日目标
- 解决 AI 输出”不结构化，不可靠“的工程难题
- 掌握 Pydantic + JSON Mode 工业级方案

### ✅ 完成情况
- [x] 朴素方法：靠 prompt 让 AI 输出 JSON（不可靠）
- [x] JSON Mode：用 `response_format` 强制合法 JSON
- [x] 终极方案：Pydantic schema 入 prompt + 校验返回值
- [x] 实战订票场景，体验"AI 接入业务系统"

### 💡 关键收获
- **裸奔输出 JSON 不可靠**， AI 经常加 markdown 包裹或解释
- **JSON Mode** 解决“格式合法”但不解决“字段错误”
- **Pydantic 校验** 是真正的业务护城河
- **4 层防御**：Prompt → JSON Mode → Pydantic →  函数签名
- 这就是 LangChain 等框架的底层原理

### 📌 明日计划
- 学习 FastAPI：把 Python 函数变成 Web 接口
- 为“DeepChat 服务化”做准备


## Day 7 - 2026-05-13（周三）

### 🎯 今日目标
- 学习 FastAPI，把 Python 函数变成 Web 接口
- 把 DeepChat 的能力包装成 Web API

### ✅ 完成情况
- [x] FastAPI Hello World：路径参数、查询参数、POST + Pydantic
- [x] 体验 `/docs` 自动生成的交互式 API 文档
- [x] AI 单轮对话 API（带成本返回）
- [x] **DeepChat 服务化**：用 session_id 实现多轮记忆
- [x] HTTPException 标准错误返回
- [x] 4 个端点：POST /chat、GET /sessions、GET /sessions/{id}、DELETE /sessions/{id}

### 💡 关键收获
- **FastAPI = Pydantic + 装饰器**，会 Pydantic 就基本会 FastAPI
- **`/docs` 是杀手级特性**，不用写文档自动生成
- **HTTP 无状态**，靠 session_id 在服务端维护"记忆"
- **uvicorn --reload** 开发模式自动重启
- **HTTPException** 是标准错误返回方式，比直接 raise Exception 更专业

### 📌 明日计划
- 思考：内存字典存会话有什么问题？（重启丢失、不能多机器）
- 学习把会话存到 Redis / 数据库



## Day 8 - 2026-05-14（周四）

### 🎯 今日目标
- 学习 SQLite + SQLAlchemy
- 把 DeepChat 会话持久化到数据库

### ✅ 完成情况
- [x] 用纯 SQL 完成 CRUD 4 个动作
- [x] 学会 SQLAlchemy ORM：Python 类 = 数据表
- [x] DeepChat 会话存数据库
- [x] **服务重启验证**：数据真的不丢了 ✅
- [x] 学会 FastAPI 依赖注入 `Depends(get_db)`

### 💡 关键收获
- **持久化的本质**：数据从内存搬到磁盘
- **ORM 的价值**：用对象代替 SQL，类型安全 + 跨数据库
- **依赖注入**：FastAPI 自动管理数据库连接的生命周期
- **数据库不能推 GitHub**：包含用户隐私
- **SQLite 适合中小规模**，更大并发要 PostgreSQL/MySQL

### 📌 明日计划
- 周末复盘 + 部署到云端，让全世界能访问