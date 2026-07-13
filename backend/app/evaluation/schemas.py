"""离线 Agent 评测数据结构。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import AgentCapabilities
from app.schemas.github import RepositorySummary
from app.schemas.search import ParsedRequirement


class RequirementEvaluationCase(BaseModel):
    """一条自然语言需求及其期望结构化结果。"""

    model_config = ConfigDict(frozen=True)

    id: str
    query: str
    expected: ParsedRequirement


class ResearchEvaluationCase(BaseModel):
    """无需访问 GitHub 即可重放的仓库研究资料。"""

    model_config = ConfigDict(frozen=True)

    id: str
    repository: RepositorySummary
    readme_path: str = "README.md"
    readme_content: str
    tree_paths: list[str] = Field(default_factory=list)
    dependency_files: dict[str, str] = Field(default_factory=dict)
    expected_capabilities: AgentCapabilities
    expected_wrapper_risk: Literal["low", "medium", "high", "unknown"]
    expected_evidence_sources: list[str] = Field(default_factory=list)


class AgentEvaluationDataset(BaseModel):
    """版本化的固定评测集。"""

    model_config = ConfigDict(frozen=True)

    version: str
    requirement_cases: list[RequirementEvaluationCase] = Field(min_length=1)
    research_cases: list[ResearchEvaluationCase] = Field(min_length=1)
    expected_top_repository: str


class AgentEvaluationReport(BaseModel):
    """可由 CI 和文档共同消费的评测结果。"""

    model_config = ConfigDict(frozen=True)

    dataset_version: str
    evaluation_mode: str = "offline_deterministic"
    requirement_case_count: int
    research_case_count: int
    requirement_field_accuracy: float = Field(ge=0, le=1)
    search_query_validity_rate: float = Field(ge=0, le=1)
    excluded_term_leakage_rate: float = Field(ge=0, le=1)
    capability_detection_accuracy: float = Field(ge=0, le=1)
    wrapper_risk_accuracy: float = Field(ge=0, le=1)
    irrelevant_filter_recall: float = Field(ge=0, le=1)
    recommendation_precision_at_1: float = Field(ge=0, le=1)
    reading_path_hallucination_rate: float = Field(ge=0, le=1)
    evidence_source_coverage_rate: float = Field(ge=0, le=1)
    model_call_count: int = 0
    tool_call_count: int = 0
