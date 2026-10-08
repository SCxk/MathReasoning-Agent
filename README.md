# MathReasoning-Agent

MathReasoning-Agent 是一个数学推理 Web 应用，提供聊天解题、公式展示、题目文件上传、会话历史、任务进度与取消/恢复。

前端使用 React、TypeScript 和 Vite；后端使用 FastAPI 和 LangGraph，复用本地推理引擎完成题型识别、策略检索、求解、审查和修复。Redis 可持久化本地聊天记录；PostgreSQL/Celery 部署作为独立选项保留。

本仓库提供独立应用源码，不包含竞赛提交入口、题目数据、离线答案评测工具或本地模型权重。

## 目录

| 路径 | 用途 |
| --- | --- |
| `client/` | React 聊天前端 |
| `agent_platform/` | HTTP/SSE API、任务调度、历史记录、文件解析和存储 |
| `reasoning_agent/` | 后端复用的推理引擎、提示词、解析器与算式检查 |
| `deployment_bootstrap.py`、`llm_client.py` | 后端模型连接；凭据从环境变量读取 |
| `skill2_en/`、`skill2/` | 数学技能材料及中文回退材料 |
| `strategy_data/` | 本地策略语料和检索索引 |
| `strategyrag/` | 上游资源说明；可选模型权重需另行准备，普通聊天不需要 |
| `deploy/`、`Dockerfile`、`compose*.yaml` | Redis 配置及可选容器部署 |
| `tests/`、`scripts/` | 功能回归、浏览器检查、运维及技能维护 |
| `docs/` | 当前应用架构说明 |
| `local_state/` | 运行时创建的聊天记录和题目目录，不随源码发布 |

`reasoning_agent/` 中的共享配置、解析器和策略卡仍被后端导入。默认 Web 流程由 `agent_platform/staged_adapter.py` 和 `graph_runtime.py` 驱动，不经过旧的模式工厂。随附的策略资源仅用于检索方法，不是题目评测集；详见 [资源说明](strategy_data/README.md)。

## 环境与安装

建议 Python 3.11、Node.js >=22.12；需要重启后保留历史记录时，还需安装 Redis。

从项目根目录执行，以下示例使用 PowerShell：

```powershell
python -m venv .venv-platform
.\.venv-platform\Scripts\python.exe -m pip install -r requirements.txt
cd client
npm.cmd ci
npm.cmd run build
cd ..
```

`requirements.txt` 安装 Web 后端及存储/部署依赖，不再默认安装旧的 lagent 或嵌入模型运行时。可选文档 RAG 另装 `requirements-platform-m5.txt`；开发检查另装 `requirements-platform-dev.txt`。

## 启动真实解题

在后端终端设置模型连接：

```powershell
$env:INTERN_API_KEY = "<your-api-key>"
$env:INTERN_MODEL = "intern-s2-preview"
```

默认服务地址为 Intern API；兼容的接口可以用 `INTERN_API_BASE` 配置。密钥只放后端环境变量，前端不接触模型凭据。

先在另一个终端启动专用 Redis：

```powershell
New-Item -ItemType Directory -Force local_state/chat_redis | Out-Null
redis-server deploy/redis-chat.conf
```

然后启动后端：

```powershell
$env:MATHS_CHAT_REDIS_URL = "redis://127.0.0.1:6388/0"
.\.venv-platform\Scripts\python.exe -m agent_platform --port 8010 --runtime langgraph --client-provider deployment_bootstrap:provided_client --client-identity intern/intern-s2-preview/local-v1 --function-calling off --redis-url-env MATHS_CHAT_REDIS_URL --namespace maths:chat:v1 --question-dir local_state/chat_questions
```

打开 [聊天页面](http://127.0.0.1:8010/chat/)；API 文档位于 [/docs](http://127.0.0.1:8010/docs)。示例使用 8010 避开常用开发端口，端口占用时可另选。

`--client-identity` 应与实际模型和版本对应。Redis 要开启 AOF 和 `appendfsync always`，否则后端拒绝声称数据可持久化。保留原来的 Redis 目录、命名空间与题目目录即可继续访问原聊天历史；更换这些配置不会自动迁移记录。

启动真实流程后，提交问题会调用模型并消耗额度。代码或配置更新后，旧的未完成任务可能因检查点版本不兼容而无法恢复，已完成历史仍可访问。

## 无模型演示与前端开发

只检查界面和 API 时，可以运行不调用模型的演示后端：

```powershell
.\.venv-platform\Scripts\python.exe -m agent_platform --port 8010
```

该模式会明确标注 Fake，只返回演示结果；内存记录在进程退出后丢失。

开发前端时，在另一个终端执行：

```powershell
cd client
$env:MATHS_BACKEND_URL = "http://127.0.0.1:8010"
npm.cmd run dev -- --port 5174
```

打开 [开发页面](http://127.0.0.1:5174/chat/)。正式前端构建产物输出到 `agent_platform/static/chat/`，由后端直接提供，无需另外运行 Node 服务。

## 功能与边界

- 支持文本问题、PDF/Markdown 题目文件、数学公式、回答详略选择和 Markdown 导出。
- 上传文件先解析，用户发送后才开始逐题求解；扫描 PDF 的 OCR 尚不支持。
- 提供任务进度、取消、会话历史及中断任务的显式恢复。
- 普通聊天不启用参考文档 RAG，不需要下载嵌入权重；可选后端 RAG 仍保留。
- 当前面向本地单用户，服务绑定回环地址；公开部署前需要单独配置身份认证与访问隔离。
- 独立审查与修复属于解题功能，不能将它们当作离线评测代码删除。

后端配置与可选分布式部署见 [后端说明](agent_platform/README.md)，前端行为见 [前端说明](client/README.md)。

## 开发检查

```powershell
.\.venv-platform\Scripts\python.exe -m pip install -r requirements-platform-dev.txt
.\.venv-platform\Scripts\python.exe -m pytest -q
cd client
npm.cmd test
npm.cmd run build
```

完整 CI 另运行 `python scripts/check_platform_ci.py`，需要通过 `MATHS_TEST_DATABASE_URL` 提供专用测试 PostgreSQL。没有测试数据库时相关集成测试会跳过；完整覆盖率门槛可能无法通过。功能测试使用 Fake 或模拟模型，不需要真实 API 请求。

## 上传 GitHub 前

仅提交源码、配置、技能材料和必要的策略资源。不要上传密钥、聊天记录、题目数据、日志、生成结果、缓存或本地环境。

这是不含旧 Git 历史的源码发布副本，尚未初始化 Git。首次上传步骤见 [发布说明](PUBLISHING.md)。改 GitHub 仓库名不需要改 Python 导入路径；上游资源声明保留在 [第三方说明](THIRD_PARTY_NOTICES.md) 中。
