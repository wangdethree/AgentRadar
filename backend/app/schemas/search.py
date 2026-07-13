"""智能搜索的结构化输入、计划和候选数据。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import RecommendationCard
from app.schemas.github import RepositorySummary

Difficulty = Literal["beginner", "intermediate", "advanced", "any"]
SearchGoal = Literal["learn", "resume_project", "reference", "secondary_development"]
ResearchLevel = Literal["skip", "shallow", "deep"]


class ParsedRequirement(BaseModel):
    """从自然语言需求中提取的稳定条件。"""

    model_config = ConfigDict(frozen=True)

    topics: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    preferred_technologies: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    difficulty: Difficulty = "any"
    goal: SearchGoal = "learn"
    excluded_features: list[str] = Field(default_factory=list)


class SearchQuery(BaseModel):
    """单条 GitHub 查询及其调查目的。"""

    model_config = ConfigDict(frozen=True)

    query: str
    purpose: str
    max_results: int = Field(default=20, ge=1, le=100)


class SearchPlan(BaseModel):
    """本轮搜索计划和工具预算。"""

    model_config = ConfigDict(frozen=True)

    queries: list[SearchQuery] = Field(min_length=3, max_length=5)
    max_candidates: int = Field(default=60, ge=3, le=100)
    max_research_targets: int = Field(default=5, ge=1, le=5)
    max_search_rounds: int = Field(default=2, ge=1, le=3)
    updated_after: datetime | None = None


class ScreenedRepository(BaseModel):
    """初筛后的仓库及可解释评分。"""

    model_config = ConfigDict(frozen=True)

    repository: RepositorySummary
    relevance_score: float = Field(ge=0, le=100)
    research_level: ResearchLevel
    reasons: list[str] = Field(default_factory=list)


class SearchSessionCreate(BaseModel):
    """创建搜索会话的请求。"""

    query: str = Field(min_length=3, max_length=2000)


class SearchSessionRefine(BaseModel):
    """在当前搜索会话中追加筛选条件。"""

    feedback: str = Field(min_length=2, max_length=1000)


class SearchSessionResponse(BaseModel):
    """搜索会话状态响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_query: str
    parsed_requirement: dict[str, object] | None
    search_plan: dict[str, object] | None
    status: str
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None


class ExecutionTraceResponse(BaseModel):
    """前端可展示的执行轨迹。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    node_name: str
    event_type: str
    input_summary: str | None
    output_summary: str | None
    duration_ms: int | None
    token_usage: int | None
    tool_names: list[str]
    error_message: str | None
    created_at: datetime


class SearchResultResponse(BaseModel):
    """搜索阶段结果及其仓库摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    relevance_score: float | None
    final_score: float | None
    rank: int | None
    reason: list[str]
    repository: RepositorySummary


class SearchExecutionResponse(BaseModel):
    """一次基础搜索工作流的即时结果。"""

    session: SearchSessionResponse
    discovered_count: int
    filtered_count: int
    screened_count: int
    research_targets: list[ScreenedRepository] = Field(default_factory=list)
    final_recommendations: list[RecommendationCard] = Field(default_factory=list)
    llm_call_count: int = 0
    errors: list[dict[str, object]] = Field(default_factory=list)
