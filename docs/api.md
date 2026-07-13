# AgentRadar API

当前接口前缀为 `/api/v1`，交互式 OpenAPI 文档位于 `/docs`。

## 仓库搜索

```http
GET /api/v1/repositories/search?q=langgraph%20language%3APython&page=1&per_page=10
```

该接口执行以下动作：

1. 调用 GitHub REST API；
2. 将原始响应裁剪为稳定的 `RepositorySummary`；
3. 使用 `github_id` 或 `full_name` 更新本地仓库；
4. 保存当前 Star、Fork 和 Issue 指标快照；
5. 返回本次搜索页。

## 仓库研究资料

```http
GET /api/v1/repositories/{owner}/{repo}
GET /api/v1/repositories/{owner}/{repo}/readme
GET /api/v1/repositories/{owner}/{repo}/tree?ref=main&depth=3
```

README 默认最多读取 300 KB，普通文件默认最多读取 200 KB。目录树默认深度为 3，最多返回 1000 项，避免把无关大段内容送入模型。

## 错误格式

GitHub 请求失败时统一返回：

```json
{
  "detail": "API rate limit exceeded",
  "code": "github_rate_limit",
  "retryable": true,
  "rate_limit_reset": 1900000000
}
```

响应不会包含 GitHub Token、请求头或内部堆栈。

## 智能搜索会话

```http
POST /api/v1/search/sessions
Content-Type: application/json

{
  "query": "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理"
}
```

基础工作流会依次完成需求解析、搜索计划、GitHub 搜索、去重过滤、候选初筛、研究目标选择和持久化。相关查询接口：

```http
GET /api/v1/search/sessions/{session_id}
GET /api/v1/search/sessions/{session_id}/results
GET /api/v1/search/sessions/{session_id}/traces
```

工作流随后会对最多五个目标读取 README、目录、依赖文件、Release 和 Issue，输出最多三个最终推荐。每个推荐包含六维评分、能力证据、工程分析、优缺点、套壳风险和来自真实目录的阅读路径。

如果首轮结果还需要收窄，可以在同一个会话中追加条件：

```http
POST /api/v1/search/sessions/{session_id}/refine
Content-Type: application/json

{
  "feedback": "只保留最近半年更新、不要 CrewAI、优先简单项目"
}
```

继续筛选会复用当前候选仓库和已经保存的分析报告，不会再次执行 GitHub 全量搜索。新的要求、筛选结果、最终推荐和 `refine_session` 执行轨迹仍保存在原会话中。

## 单仓库分析

```http
POST /api/v1/repositories/{owner}/{repo}/analyze?report_type=deep
GET  /api/v1/repositories/{owner}/{repo}/analysis?report_type=deep
```

`analyze` 会消耗 GitHub API 配额并保存报告；`analysis` 只读取本地最新报告。

## 热门项目雷达

```http
GET /api/v1/trending/daily
GET /api/v1/trending/weekly
GET /api/v1/trending/potential
GET /api/v1/trending/categories
```

榜单支持 `limit` 和 `category` 查询参数。趋势响应同时显示热度分、质量分、Agent 能力完整度和快照置信度。设置 `TRENDING_SCHEDULER_ENABLED=true` 后，单进程部署会按照配置间隔自动采集固定主题；多副本部署应将任务迁移到独立 Worker。

## 收藏与忽略

```http
POST   /api/v1/favorites
GET    /api/v1/favorites
DELETE /api/v1/favorites/{favorite_id}

POST   /api/v1/ignored-repositories
GET    /api/v1/ignored-repositories
DELETE /api/v1/ignored-repositories/{ignored_id}
```

收藏支持记录来源会话和个人备注。忽略列表会在智能搜索的规则过滤阶段生效，避免消耗后续深度研究资源；删除忽略记录后，该仓库可以再次进入候选集。
