"""证据化仓库研究与推荐数据结构。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.github import RepositorySummary

RiskLevel = Literal["low", "medium", "high", "unknown"]
RecommendationLevel = Literal["strong", "recommended", "consider"]


class EvidenceItem(BaseModel):
    """支持分析结论的真实来源。"""

    model_config = ConfigDict(frozen=True)

    source: str
    path: str | None = None
    observation: str


class ReadingPathItem(BaseModel):
    """真实存在的文件及建议阅读原因。"""

    model_config = ConfigDict(frozen=True)

    path: str
    reason: str


class AgentCapabilities(BaseModel):
    """常见 Agent 能力的证据化识别结果。"""

    model_config = ConfigDict(frozen=True)

    tool_calling: bool = False
    state_management: bool = False
    workflow_orchestration: bool = False
    multi_round_execution: bool = False
    memory: bool = False
    human_in_the_loop: bool = False
    persistence: bool = False
    evaluation: bool = False


class EngineeringAnalysis(BaseModel):
    """项目工程完整度检查结果。"""

    model_config = ConfigDict(frozen=True)

    has_api: bool = False
    has_tests: bool = False
    has_docker: bool = False
    has_database: bool = False
    has_configuration: bool = False
    has_documentation: bool = False
    dependency_files: list[str] = Field(default_factory=list)
    file_count: int = 0


class ResearchReportData(BaseModel):
    """单个仓库的浅层或深层研究报告。"""

    model_config = ConfigDict(frozen=True)

    repository: RepositorySummary
    report_type: Literal["shallow", "deep"]
    project_summary: str
    agent_capabilities: AgentCapabilities
    engineering_analysis: EngineeringAnalysis
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    reading_path: list[ReadingPathItem] = Field(default_factory=list)
    wrapper_risk: RiskLevel = "unknown"


class ScoreBreakdown(BaseModel):
    """总分 100 的六维个性化评分。"""

    model_config = ConfigDict(frozen=True)

    relevance: float = Field(ge=0, le=30)
    technology_match: float = Field(ge=0, le=20)
    agent_completeness: float = Field(ge=0, le=20)
    engineering_completeness: float = Field(ge=0, le=15)
    activity: float = Field(ge=0, le=10)
    difficulty_match: float = Field(ge=0, le=5)

    @property
    def total(self) -> float:
        """返回保留一位小数的总分。"""
        return round(
            self.relevance
            + self.technology_match
            + self.agent_completeness
            + self.engineering_completeness
            + self.activity
            + self.difficulty_match,
            1,
        )


class RecommendationCard(BaseModel):
    """最终推荐卡。"""

    model_config = ConfigDict(frozen=True)

    repository: RepositorySummary
    score: ScoreBreakdown
    total_score: float = Field(ge=0, le=100)
    recommendation_level: RecommendationLevel
    match_points: list[str] = Field(default_factory=list)
    report: ResearchReportData
