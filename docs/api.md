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
