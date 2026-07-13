"""智能搜索工作流状态。"""

from typing import TypedDict

from app.schemas.github import RepositorySummary
from app.schemas.search import ParsedRequirement, ScreenedRepository, SearchPlan


class SearchSessionState(TypedDict, total=False):
    """节点之间只传递结构化数据和计数，不保存超长原文。"""

    session_id: str
    user_query: str
    parsed_requirement: ParsedRequirement
    search_plan: SearchPlan
    discovered_repositories: list[RepositorySummary]
    filtered_repositories: list[RepositorySummary]
    screened_repositories: list[ScreenedRepository]
    research_targets: list[ScreenedRepository]
    search_round: int
    tool_call_count: int
    llm_call_count: int
    errors: list[dict[str, object]]

