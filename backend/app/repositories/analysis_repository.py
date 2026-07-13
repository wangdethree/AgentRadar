"""分析报告的数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisReport
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.analysis import (
    AgentCapabilities,
    EngineeringAnalysis,
    EvidenceItem,
    ReadingPathItem,
    ResearchReportData,
)
from app.schemas.github import RepositorySummary


class AnalysisReportRepository:
    """保存并复用仓库研究报告。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, report: ResearchReportData) -> AnalysisReport:
        """保存结构化报告和证据。"""
        repository = RepositoryRepository(self.session).upsert(report.repository)
        record = AnalysisReport(
            repository_id=repository.id,
            report_type=report.report_type,
            project_summary=report.project_summary,
            agent_capabilities=report.agent_capabilities.model_dump(mode="json"),
            engineering_analysis=report.engineering_analysis.model_dump(mode="json"),
            strengths=report.strengths,
            weaknesses=report.weaknesses,
            evidence=[item.model_dump(mode="json") for item in report.evidence],
            reading_path=[item.model_dump(mode="json") for item in report.reading_path],
            wrapper_risk=report.wrapper_risk,
            prompt_version="rules-v1",
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_latest(self, repository_id: int, report_type: str) -> AnalysisReport | None:
        """读取仓库指定类型的最新报告。"""
        statement = (
            select(AnalysisReport)
            .where(
                AnalysisReport.repository_id == repository_id,
                AnalysisReport.report_type == report_type,
            )
            .order_by(AnalysisReport.created_at.desc(), AnalysisReport.id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    @staticmethod
    def to_schema(record: AnalysisReport) -> ResearchReportData:
        """把持久化报告恢复为 API 数据结构。"""
        return ResearchReportData(
            repository=RepositorySummary.model_validate(record.repository),
            report_type="deep" if record.report_type == "deep" else "shallow",
            project_summary=record.project_summary,
            agent_capabilities=AgentCapabilities.model_validate(record.agent_capabilities),
            engineering_analysis=EngineeringAnalysis.model_validate(record.engineering_analysis),
            strengths=record.strengths,
            weaknesses=record.weaknesses,
            evidence=[EvidenceItem.model_validate(item) for item in record.evidence],
            reading_path=[ReadingPathItem.model_validate(item) for item in record.reading_path],
            wrapper_risk=record.wrapper_risk,
        )
