# SeaCost AI - 海鲜酒楼全链路成本管控系统

## 项目概述

SeaCost AI 是一个面向海鲜酒楼的全链路成本管控 AI Agent 系统，基于 Python 构建，具备智能采购报货、标准化验收入库、精细化库存管理、自动成本核算四大核心能力。系统采用三路融合意图识别、多 Agent 路由编排、三级记忆架构、动态 Skills 注入、Monitor 闭环监控和端到端评测等七大核心技术亮点。

## 技术栈

- **语言**：Python 3.12
- **Web 框架**：FastAPI + Uvicorn
- **LLM**：Anthropic Claude（兼容 DeepSeek 等第三方 API）
- **工作记忆**：Redis 7
- **情景记忆 + 用户画像 + 知识库**：ChromaDB 0.5.23（向量数据库）
- **监控**：Prometheus + Grafana
- **部署**：Docker + docker-compose
- **前端**：轻量级 HTML/CSS/JS Dashboard

## 目录结构

```
EchoMind/
├── api/                  # FastAPI 入口与路由
│   └── main.py           # 主应用入口，lifespan 管理
├── agents/               # Agent 编排
│   └── agent_orchestrator.py  # 多 Agent 路由与协作
├── core/                 # 核心能力
│   ├── intent_recognizer.py   # 三路融合意图识别
│   └── skill_loader.py        # 动态 Skills 加载与注入
├── memory/               # 记忆系统
│   └── conversation_memory.py # 三级记忆管理
├── mcp/                  # 工具调用（Model Context Protocol）
│   ├── tool_manager.py       # 工具管理器（熔断、缓存、降级）
│   └── knowledge_base.py     # RAG 知识库
├── monitor/              # 性能监控
│   └── performance_monitor.py # Monitor 闭环监控与自动降权
├── evaluation/           # 评测系统
│   └── evaluator.py      # 端到端评测（LLM-as-Judge）
├── skills/               # 动态 Skills（SOP 文档）
│   ├── purchase_sop/     # 智能采购报货 SOP
│   ├── inventory_sop/    # 标准化验收入库 SOP
│   └── cost_sop/         # 自动成本核算 SOP
├── static/               # 前端 Dashboard
│   └── index.html        # 可视化界面
├── config/               # 配置文件
│   ├── prometheus.yml
│   ├── alerts/
│   ├── grafana/
│   └── nginx/
├── data/                 # 数据目录
├── logs/                 # 日志目录
├── .env                  # 环境变量（实际配置）
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
├── Dockerfile            # 多阶段 Docker 构建
├── docker-compose.yml    # 服务编排
└── scripts/              # 部署脚本
    ├── setup.sh
    └── http_run.sh
```

## 关键入口 / 核心模块

- **API 入口**：`api/main.py` — FastAPI 应用，端口 8000
- **前端 Dashboard**：`static/index.html` — 可视化界面
- **Agent 编排**：`agents/agent_orchestrator.py` — 多 Agent 路由与协作
- **意图识别**：`core/intent_recognizer.py` — 三路融合（LLM + Embedding + Pattern）
- **Skills 加载**：`core/skill_loader.py` — 动态 SOP 注入
- **记忆系统**：`memory/conversation_memory.py` — Redis + ChromaDB 三级记忆
- **工具管理**：`mcp/tool_manager.py` — MCP 工具调用（熔断、缓存、降级）
- **知识库**：`mcp/knowledge_base.py` — RAG 向量检索
- **性能监控**：`monitor/performance_monitor.py` — Monitor 闭环监控
- **评测系统**：`evaluation/evaluator.py` — 端到端评测

## 七大核心技术亮点

### 1. 三路融合意图识别
- LLM 语义理解（权重 70%）+ Embedding 向量相似度（权重 20%）+ 关键词模式匹配（权重 10%）
- 支持 8 种餐饮意图：采购、库存、成本、查询、投诉、问候、反馈、其他
- 加权投票合并结果，低置信度降级保护

### 2. MCP 工具调用 + RAG 知识库
- 查询改写（Query Rewriting）→ 并行召回 → LLM 重排（Reranking）
- 熔断器 + TTL 缓存 + 降级策略（Fallback）
- ChromaDB 向量检索，支持文档上传和自动切片

### 3. 三级记忆管理
- 工作记忆：Redis（最近 20 条，TTL 24h）
- 情景记忆：ChromaDB（对话摘要，语义检索）
- 用户画像：ChromaDB（偏好提炼，异步更新）
- 自动压缩（15 条触发），避免 context 膨胀

### 4. 多 Agent 路由编排
- 采购 Agent（智能报货）、库存 Agent（验收管理）、成本 Agent（核算分析）
- 三层路由：意图路由 → 性能路由 → 降级路由
- 自动并行协作（复合问题检测）

### 5. 动态 Skills 注入
- Markdown 格式 SOP 文档，按 Agent 类型匹配注入
- 关键词触发规则，热加载无需重启
- 长度预算控制，避免挤占记忆和知识库上下文

### 6. Monitor 闭环监控
- 实时采集 Agent/Tool 指标，Z-score 异常检测
- 自动降权（routing_penalty），影响后续路由决策
- Prometheus 指标暴露，Webhook 告警

### 7. 端到端评测
- 意图识别 Accuracy/Macro-F1
- LLM-as-Judge 四维评分（相关性、准确性、完整性、有用性）
- 多轮对话评测，回归检测（基线对比）
- 自动优化建议生成

## 运行与预览

- **开发启动**：`cd EchoMind && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- **前端访问**：浏览器打开 `http://localhost:8000/`
- **API 文档**：`http://localhost:8000/docs`（Swagger UI）
- **Docker 部署**：`docker-compose up -d`（包含 Redis、ChromaDB、Prometheus、SeaCost AI）
- **健康检查**：`GET /health`

## 用户偏好与长期约束

- Python 项目使用 `uv` 管理依赖和虚拟环境
- LLM 集成默认使用流式返回
- 环境变量通过 `.env` 文件管理，敏感信息不提交到 Git
- 当前 LLM 配置为 DeepSeek（兼容 Anthropic 协议）

## 常见问题和预防

- ChromaDB 首次启动需下载 ONNX 模型（~79MB），Dockerfile 已预下载
- Redis 和 ChromaDB 通过 docker-compose 内部网络通信，容器间使用服务名作为主机名
- 本地开发时需单独启动 Redis 和 ChromaDB，或修改 `.env` 中的连接地址
- Skills 文件位于 `skills/` 目录，修改后调用 `/skills/reload` 热加载
