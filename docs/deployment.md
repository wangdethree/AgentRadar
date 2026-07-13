# AgentRadar 部署说明

## Docker Compose 快速启动

要求 Docker Engine 24+ 与 Docker Compose v2。项目后端镜像固定使用 Python 3.11，前端构建使用 Node.js 22，数据库使用 PostgreSQL 16。

```bash
cp .env.example .env
```

至少修改 `.env` 中的 `POSTGRES_PASSWORD` 和 `COMPOSE_DATABASE_URL`，二者密码必须一致。建议同时配置 `GITHUB_TOKEN`，否则 GitHub 匿名 API 配额较低。

模型增强是可选能力。接入兼容 OpenAI Chat Completions 协议的服务时设置：

```dotenv
LLM_API_KEY=replace-with-secret
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=your-model-name
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=1
```

`LLM_BASE_URL` 可以填写 API 根地址，也可以直接填写以 `/chat/completions` 结尾的完整地址。只有 `LLM_BASE_URL` 和 `LLM_MODEL` 同时存在时才启用模型；不需要鉴权的本地服务可以留空 `LLM_API_KEY`。服务必须支持 Chat Completions 的 JSON 响应和 `response_format={"type":"json_object"}`。模型不可用时搜索会降级到确定性规则，因此无需把模型健康状态加入容器启动依赖。

```bash
docker compose up --build -d
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8080/healthz
```

访问地址：

- 前端统一入口：<http://localhost:8080>；
- FastAPI OpenAPI：<http://localhost:8000/docs>；
- 后端健康检查：<http://localhost:8000/health>。

后端容器会先执行 `alembic upgrade head`，成功后才启动 Uvicorn。PostgreSQL 数据保存在 `postgres-data` 命名卷中，普通的容器重建不会清空数据。

## 加载稳定 Demo 数据

服务健康后执行：

```bash
docker compose exec backend python -m app.demo
```

命令会写入 3 个演示仓库、9 个趋势快照和 3 份分析报告。重复运行会覆盖这些演示仓库的快照和报告，不会持续累积重复数据。刷新首页后，“今日热门”“本周上升”“新项目潜力”都会有稳定内容。

演示仓库名称以 `agentradar-demo/` 开头，GitHub 链接仅用于界面展示；指标和分析明确来自固定数据，不应当作实时 GitHub 事实。

## 常用运维命令

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend alembic current
docker compose exec backend python -m app.evaluation evaluation/agent_cases.json
docker compose restart backend
docker compose down
```

只有明确需要清空数据库时才执行 `docker compose down -v`。该命令会删除 PostgreSQL 命名卷中的全部数据。

## 本地非容器启动

```bash
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/python -m app.demo
.venv/bin/uvicorn app.main:app --reload
```

另开终端：

```bash
cd frontend
npm install
npm run dev
```

本地默认使用 `backend/agentradar.db` SQLite 文件。若改用 PostgreSQL，设置 `DATABASE_URL=postgresql+psycopg://...` 后重新执行迁移。

## 生产注意事项

- 使用密钥管理服务注入 GitHub Token、模型密钥和数据库密码，不要提交 `.env`；
- `DEBUG=false`，并把 `BACKEND_CORS_ORIGINS` 限制为实际域名；
- TLS 应在反向代理或云负载均衡终止；
- 定期备份 PostgreSQL，并在升级前验证 Alembic 迁移；
- 多后端副本时关闭各副本的 `TRENDING_SCHEDULER_ENABLED`，改由单独 Worker 调度；
- 对 GitHub API 错误率、限流剩余量、模型降级率与令牌量、搜索耗时和失败会话建立监控。

## 当前验证范围

Compose 配置会在本地和 CI 前检查；后端迁移、单元/集成测试与前端生产构建均可独立验证。若本机 Docker daemon 未启动，只能验证配置，无法完成镜像构建和容器健康检查，发布前应在有 Docker daemon 的环境补跑完整启动流程。
