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

## Day 9 - 2026-05-19（周一）

### 🎯 今日目标
- 学习 Docker 容器化
- 把 DeepChat 部署到 Render 云端

### ✅ 完成情况
- [x] 理解部署三要素：代码、环境、运行命令
- [x] 编写 Dockerfile + .dockerignore
- [x] 本地用 Docker 跑通 DeepChat
- [x] 注册 Render，连接 GitHub 仓库
- [x] 配置环境变量（API Key 安全管理）
- [x] **DeepChat 正式上线** 🚀
- [x] 把在线 URL 加到 README

### 💡 关键收获
- **Docker = 集装箱**，解决"在我电脑能跑"的玄学
- **环境变量** 是云上管理密钥的标准方式
- **CI/CD 雏形**：git push → Render 自动部署
- **HTTPS 免费拿** —— Render 自动配 SSL
- **冷启动**：免费层 15 分钟无访问会休眠，下次访问慢一点

### 🐛 踩过的坑
- 拉不下 Docker 官方镜像，配置国内镜像源
- 

### 📌 明日计划
- 学习 RAG 入门：让 AI 读你的文档
- 理解 Embedding 和"向量"概念

## Day 10 - 2026-05-20（周二）

### 🎯 今日目标
- 理解 RAG 核心原理
- 实现"最小可用 RAG"系统

### ✅ 完成情况
- [x] 申请硅基流动 API（免费 Embedding）
- [x] 体验 Embedding：感受"语义距离" vs "字面匹配"
- [x] 学会两种分块策略：按字数 / 按段落
- [x] 实现 MiniRAG 类：build_index + retrieve + ask
- [x] **AI 成功回答了关于"王兴"的私人问题** 🎯

### 💡 关键收获
- **Embedding = 文字的数学指纹**，意思相近 → 向量相近
- **RAG ≠ 微调**：RAG 是"翻书答题"，不改变模型
- **余弦相似度**：判断两个向量相似度的标准方法
- **分块是艺术**：太大浪费 token、太小丢失上下文
- **System prompt 强约束**："只根据参考资料回答"防止幻觉

### 🤔 思考
- 我们每次都重新算 embeddings，**实际生产怎么持久化向量？**
- 文档越来越多时，挨个算相似度会很慢，**怎么加速检索？**

### 📌 明日计划
- 学习向量数据库（ChromaDB / FAISS）
- 解决"向量持久化"和"检索加速"问题


## Day 11 - 2026-05-21（周三）

### 🎯 今日目标
- 学习向量数据库 ChromaDB
- 解决 Day 10 的两大痛点：持久化 + 检索加速

### ✅ 完成情况
- [x] ChromaDB 入门：增删改查 + 元数据
- [x] 用 ChromaDB 重写 RAG，集成硅基流动 bge-m3
- [x] **upsert 实现幂等入库**（重复运行不会重算）
- [x] 多文档管理 + 元数据过滤
- [x] 体验"权限隔离"场景

### 💡 关键收获
- **ChromaDB = SQLite 级的简单 + 向量数据库的能力**
- **HNSW 索引**：把 O(N) 暴力检索变成 O(logN)
- **upsert vs add**：用稳定 id 避免重复计算
- **元数据过滤**：企业级 RAG 必备（权限、分类、时间）
- **EmbeddingFunction**：可以自定义任何模型
- **distance vs similarity**：ChromaDB 返回距离（越小越像）

### 🤔 思考题
- 现在 RAG 是命令行版本，怎么把它接入到 DeepChat Web 服务？
- 用户上传一份新文档，怎么动态加入知识库？

### 📌 明日计划
- 把 RAG 接入 DeepChat 服务
- 实现"上传文档 + 即时问答" Web 接口

## Day 12 - 2026-05-22（周四）

### 🎯 今日目标
- 把 RAG 接入 DeepChat Web 服务
- 实现"上传文档 + 智能问答"完整闭环

### ✅ 完成情况
- [x] 设计 4 个新 API：上传/列表/删除/对话
- [x] FastAPI 文件上传：UploadFile + multipart/form-data
- [x] use_rag 开关 + kb_filter 元数据过滤
- [x] retrieved_sources 字段：让回答可追溯
- [x] 完整测试：上传 → 问答 → 删除 全流程
- [x] **DeepChat 进化为 RAG 知识库问答系统** 🎯

### 💡 关键收获
- **接口设计先于代码** —— use_rag 开关是产品思维
- **upsert 保证幂等** —— 同名文档可以反复上传更新
- **retrieved_sources** 是 RAG 系统的"可信度证据"
- **kb_filter** 让企业级权限隔离成为可能
- **会话 + 向量库 是两个独立的数据库**，各司其职

### 🤔 思考题
- 现在只支持 .txt/.md，怎么支持 PDF/Word？
- 知识库越来越大，怎么做"按用户隔离"（每个用户只能搜自己的文档）？

### 📌 下一阶段
- Day 13: Function Calling / Tool Use 入门
- Week 4: Agent 系统 —— 让 AI 主动调用工具


## Day 13 - 2026-05-25（周日 / 周一）

### 🎯 今日目标
- 理解 Function Calling 协议
- 让 AI 主动使用多个工具

### ✅ 完成情况
- [x] 单工具：get_current_time
- [x] 多工具：天气 + 时间 + 计算器
- [x] 工具循环：AI 自主决定调用次数
- [x] 边界场景：跨语言、数据缺失、推理 + 工具

### 💡 关键收获
- **Function Calling 协议 4 字段**：tools / tool_calls / tool_call_id / role:"tool"
- **LLM 不真执行函数**，只输出"想调谁、传什么"，执行是我们的代码
- **tool_choice: auto**：让 AI 自己判断要不要用工具
- **多轮循环**是 Agent 的核心模式，需要 max_iterations 防死循环
- **工具描述 description 很关键**，写得清楚 AI 才会选对

### 🤔 思考题
- 如果工具执行很慢（如查数据库 10 秒），怎么避免 LLM 干等？
- 如何让 AI 调用敏感工具（如删数据库）时需要"用户确认"？

### 📌 明日计划
- 接入真实工具：网页搜索 + 调用 DeepChat 知识库
- 把 Function Calling 接入 Web 服务


## Day 14 - 2026-05-26（周二）

### 🎯 今日目标
- 理解 ReAct 模式（推理 + 行动）
- 实现 SuperAgent：RAG + 工具自主组合

### ✅ 完成情况
- [x] 手撸 ReAct：看到 AI 的思考过程
- [x] 工业版 ReAct：Function Calling + 显式思考
- [x] **SuperAgent**：把 RAG 包装成工具，AI 自主调度
- [x] 体验"AI 自主拆解任务"的爽感

### 💡 关键收获
- **ReAct = Reasoning + Acting**，让决策可观察
- **RAG 可以"降级"为工具** —— Agent 自己决定何时查
- **System Prompt 是 Agent 的"灵魂"** —— 写得好坏决定上限
- **stop 词**让 LLM 在指定位置停下，避免脑补
- **temperature 调低** = 思考更稳定，少抽风

### 🤔 思考题
- AI 的思考过程可见 = 用户看到的内容更长 = 体验变慢，怎么办？
- 如果 Agent 卡死在一个工具反复调用（死循环），怎么自我恢复？

### 📌 明日计划
- 把 SuperAgent 接入 DeepChat Web 服务
- 加流式输出，让用户实时看到 AI 思考