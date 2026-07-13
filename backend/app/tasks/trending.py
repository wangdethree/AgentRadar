"""热门仓库定时采集任务。"""

from app.core.database import SessionLocal
from app.services.repository_service import RepositoryService
from app.tools.github.client import GitHubClient
from app.tools.github.errors import GitHubAPIError

TRENDING_QUERIES = (
    "AI Agent",
    "LangGraph",
    "Multi-Agent",
    "MCP agent",
    "Browser Agent",
    "Coding Agent",
    "Agent Memory",
    "Agent Evaluation",
    "Research Agent",
    "Workflow Agent",
)


async def collect_trending_snapshots() -> dict[str, object]:
    """按固定主题采集仓库，并为每条结果保存指标快照。"""
    repository_count = 0
    errors: list[dict[str, str]] = []
    with SessionLocal() as session:
        async with GitHubClient() as github_client:
            service = RepositoryService(session, github_client)
            for query in TRENDING_QUERIES:
                qualified_query = f"{query} fork:false archived:false"
                try:
                    page = await service.search_and_persist(qualified_query, per_page=30)
                except GitHubAPIError as error:
                    errors.append({"query": query, "code": error.code})
                    continue
                repository_count += len(page.items)
    return {
        "query_count": len(TRENDING_QUERIES),
        "repository_count": repository_count,
        "errors": errors,
    }

