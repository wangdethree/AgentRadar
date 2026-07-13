# AgentRadar

AgentRadar 是面向 AI Agent 学习者、求职者和开发者的 GitHub 项目发现、趋势分析与深度研究系统。它会把自然语言需求转换成搜索计划，对候选仓库进行规则过滤与证据化分析，最终给出可解释的项目推荐。

## 当前进度

项目正在按 V1 计划书分阶段交付：

- [x] 阶段 0：项目骨架与工程规范
- [x] 阶段 1：GitHub 数据层
- [x] 阶段 2：智能搜索基础链路
- [x] 阶段 3：深度研究与推荐
- [x] 阶段 4：热门项目雷达
- [ ] 阶段 5：前端与交互
- [ ] 阶段 6：测试、文档与部署

## 技术栈

- 后端：Python 3.11、FastAPI、Pydantic、SQLAlchemy、LangGraph
- 前端：React、TypeScript、Vite、TanStack Query
- 数据：开发环境使用 SQLite，完整 V1 支持 PostgreSQL
- 工程：pytest、Ruff、MyPy、ESLint、Prettier、Docker Compose

## 本地开发

### 后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload
```

后端启动后可访问：

- 健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/docs>

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：<http://localhost:5173>

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

容器启动后，统一入口为 <http://localhost:8080>，后端 API 仍可通过 <http://localhost:8000> 直接访问。

## 质量检查

```bash
cd backend
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest

cd ../frontend
npm run lint
npm run typecheck
npm run build
```

## 安全约定

- GitHub Token 与模型密钥不得提交到仓库；
- V1 只执行 GitHub 只读操作；
- 不自动运行被研究仓库中的代码或 Shell 命令；
- 对外部请求统一设置超时、有限重试并记录可解释错误。

## 已开放的 V1 API

- `GET /health`：容器与负载均衡健康检查；
- `GET /api/v1/repositories/search?q=...`：搜索仓库、标准化数据并保存快照；
- `GET /api/v1/repositories/{owner}/{repo}`：同步仓库详情；
- `GET /api/v1/repositories/{owner}/{repo}/readme`：读取并解码 README；
- `GET /api/v1/repositories/{owner}/{repo}/tree?ref=main&depth=3`：读取裁剪后的目录树。
- `POST /api/v1/repositories/{owner}/{repo}/analyze`：执行证据化深度分析；
- `GET /api/v1/repositories/{owner}/{repo}/analysis`：复用最新分析报告；
- `POST /api/v1/search/sessions`：执行需求解析、搜索、过滤和候选初筛；
- `GET /api/v1/search/sessions/{session_id}`：查看会话状态与搜索计划；
- `GET /api/v1/search/sessions/{session_id}/results`：查看阶段结果；
- `GET /api/v1/search/sessions/{session_id}/traces`：查看可解释执行轨迹。
- `GET /api/v1/trending/daily`：今日热门；
- `GET /api/v1/trending/weekly`：本周上升；
- `GET /api/v1/trending/potential`：新项目潜力；
- `GET /api/v1/trending/categories`：热门项目分类。

更多信息见 [API 文档](docs/api.md)。
