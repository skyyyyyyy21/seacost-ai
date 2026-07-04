# EchoMind - AGENTS.md

## 项目概述

EchoMind 是一个基于 Python 的后端 AI 智能客服系统，具备意图识别、多轮对话、三级记忆架构（工作记忆 + 情景记忆 + 用户画像）、工具调用（MCP）和性能监控能力。

## 技术栈

- **语言**：Python 3.12
- **Web 框架**：FastAPI + Uvicorn
- **LLM**：Anthropic Claude（兼容 DeepSeek 等第三方 API）
- **工作记忆**：Redis 7
- **情景记忆 + 用户画像**：ChromaDB 0.5.23（向量数据库）
- **监控**：Prometheus + Grafana
- **部署**：Docker + docker-compose

## 目录结构

```
EchoMind/
├── api/                  # FastAPI 入口与路由
│   └── main.py           # 主应用入口，lifespan 管理
├── agents/               # Agent 编排
│   └── agent_orchestrator.py
├── core/                 # 核心能力
│   └── intent_recognizer.py  # 意图识别（Embedding + LLM）
├── memory/               # 记忆系统
│   └── conversation_memory.py  # 三级记忆管理
├── mcp/                  # 工具调用（Model Context Protocol）
│   ├── tool_manager.py       # 工具管理器
│   └── knowledge_base.py     # 知识库
├── monitor/              # 性能监控
│   └── performance_monitor.py
├── evaluation/           # 评测系统
│   └── evaluator.py
├── config/               # 配置文件
│   ├── prometheus.yml
│   ├── alerts/
│   ├── grafana/
│   └── nginx/
├── data/                 # 数据目录
├── logs/                 # 日志目录
├── tools/                # 工具目录（预留）
├── .env                  # 环境变量（实际配置）
├── .env.example          # 环境变量模板
├── requirements.txt      # Python 依赖
├── Dockerfile            # 多阶段 Docker 构建
├── docker-compose.yml    # 服务编排
├── docker-deploy.sh      # Docker 部署脚本
├── build-image.sh        # 镜像构建脚本
└── run-image.sh          # 镜像运行脚本
```

## 关键入口 / 核心模块

- **API 入口**：`api/main.py` — FastAPI 应用，端口 8000
- **Agent 编排**：`agents/agent_orchestrator.py` — 对话流程编排
- **意图识别**：`core/intent_recognizer.py` — Embedding + LLM 双路意图识别
- **记忆系统**：`memory/conversation_memory.py` — Redis + ChromaDB 三级记忆
- **工具管理**：`mcp/tool_manager.py` — MCP 工具调用
- **知识库**：`mcp/knowledge_base.py` — ChromaDB 向量检索
- **性能监控**：`monitor/performance_monitor.py` — Prometheus 指标采集

## 运行与预览

- **开发启动**：`cd EchoMind && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`
- **Docker 部署**：`docker-compose up -d`（包含 Redis、ChromaDB、Prometheus、EchoMind）
- **健康检查**：`GET /health`
- **API 文档**：`GET /docs`（Swagger UI，需开启 ENABLE_SWAGGER_UI）
- **本项目为后端服务，不支持预览**

## 用户偏好与长期约束

- Python 项目使用 `uv` 管理依赖和虚拟环境
- LLM 集成默认使用流式返回
- 环境变量通过 `.env` 文件管理，敏感信息不提交到 Git
- 当前 LLM 配置为 DeepSeek（兼容 Anthropic 协议）

## 常见问题和预防

- ChromaDB 首次启动需下载 ONNX 模型（~79MB），Dockerfile 已预下载
- Redis 和 ChromaDB 通过 docker-compose 内部网络通信，容器间使用服务名作为主机名
- 本地开发时需单独启动 Redis 和 ChromaDB，或修改 `.env` 中的连接地址
