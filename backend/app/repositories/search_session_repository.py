"""搜索会话、结果与执行轨迹的数据访问。"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.search import ExecutionTrace, SearchResult, SearchSession
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.analysis import RecommendationCard
from app.schemas.search import ParsedRequirement, ScreenedRepository, SearchPlan


class SearchSessionRepository:
    """集中管理搜索状态，支持节点失败后查询已有轨迹。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, user_query: str) -> SearchSession:
        """创建待执行搜索会话。"""
        search_session = SearchSession(user_query=user_query, status="pending")
        self.session.add(search_session)
        self.session.commit()
        self.session.refresh(search_session)
        return search_session

    def get(self, session_id: str) -> SearchSession | None:
        """读取单个搜索会话。"""
        return self.session.get(SearchSession, session_id)

    def list_sessions(
        self,
        *,
        limit: int = 10,
        status: str | None = None,
    ) -> list[SearchSession]:
        """按创建时间倒序读取最近搜索历史。"""
        statement = select(SearchSession).order_by(
            SearchSession.created_at.desc(),
            SearchSession.id.desc(),
        )
        if status is not None:
            statement = statement.where(SearchSession.status == status)
        return list(self.session.scalars(statement.limit(limit)))

    def mark_running(self, search_session: SearchSession) -> None:
        """标记会话开始执行。"""
        search_session.status = "running"
        search_session.error_message = None
        search_session.finished_at = None
        self.session.commit()

    def save_plan(
        self,
        search_session: SearchSession,
        requirement: ParsedRequirement,
        plan: SearchPlan,
    ) -> None:
        """保存结构化需求与搜索计划。"""
        search_session.parsed_requirement = requirement.model_dump(mode="json")
        search_session.search_plan = plan.model_dump(mode="json")
        self.session.commit()

    def mark_completed(self, search_session: SearchSession) -> None:
        """标记基础搜索链路完成。"""
        search_session.status = "completed"
        search_session.finished_at = datetime.now(UTC)
        self.session.commit()

    def mark_failed(self, search_session: SearchSession, error: Exception) -> None:
        """保存安全的失败摘要，不记录外部请求敏感信息。"""
        search_session.status = "failed"
        search_session.error_message = str(error)[:1000]
        search_session.finished_at = datetime.now(UTC)
        self.session.commit()

    def add_trace(
        self,
        search_session: SearchSession,
        *,
        node_name: str,
        input_summary: str | None,
        output_summary: str | None,
        duration_ms: int,
        token_usage: int | None = None,
        tool_names: list[str] | None = None,
        error_message: str | None = None,
    ) -> ExecutionTrace:
        """写入前端可展示的节点轨迹。"""
        trace = ExecutionTrace(
            session_id=search_session.id,
            node_name=node_name,
            event_type="error" if error_message else "node",
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            token_usage=token_usage,
            tool_names=tool_names or [],
            error_message=error_message,
        )
        self.session.add(trace)
        self.session.commit()
        self.session.refresh(trace)
        return trace

    def replace_stage_results(
        self,
        search_session: SearchSession,
        *,
        stage: str,
        items: list[ScreenedRepository],
    ) -> None:
        """以幂等方式保存某一阶段的排序结果。"""
        self.session.execute(
            delete(SearchResult).where(
                SearchResult.session_id == search_session.id,
                SearchResult.stage == stage,
            )
        )
        repository_store = RepositoryRepository(self.session)
        for rank, item in enumerate(items, start=1):
            repository = repository_store.upsert(item.repository)
            self.session.add(
                SearchResult(
                    session_id=search_session.id,
                    repository_id=repository.id,
                    stage=stage,
                    relevance_score=item.relevance_score,
                    rank=rank,
                    reason=item.reasons,
                )
            )
        self.session.commit()

    def replace_final_results(
        self,
        search_session: SearchSession,
        recommendations: list[RecommendationCard],
    ) -> None:
        """保存最终三项推荐及其总分。"""
        self.session.execute(
            delete(SearchResult).where(
                SearchResult.session_id == search_session.id,
                SearchResult.stage == "final",
            )
        )
        repository_store = RepositoryRepository(self.session)
        for rank, card in enumerate(recommendations, start=1):
            repository = repository_store.upsert(card.repository)
            self.session.add(
                SearchResult(
                    session_id=search_session.id,
                    repository_id=repository.id,
                    stage="final",
                    relevance_score=card.score.relevance,
                    final_score=card.total_score,
                    rank=rank,
                    reason=card.match_points,
                )
            )
        self.session.commit()

    def list_results(self, session_id: str, stage: str | None = None) -> list[SearchResult]:
        """按阶段和排名读取搜索结果。"""
        statement = (
            select(SearchResult)
            .options(selectinload(SearchResult.repository))
            .where(SearchResult.session_id == session_id)
            .order_by(SearchResult.stage, SearchResult.rank)
        )
        if stage is not None:
            statement = statement.where(SearchResult.stage == stage)
        return list(self.session.scalars(statement))

    def list_traces(self, session_id: str) -> list[ExecutionTrace]:
        """按发生顺序读取会话轨迹。"""
        statement = (
            select(ExecutionTrace)
            .where(ExecutionTrace.session_id == session_id)
            .order_by(ExecutionTrace.created_at, ExecutionTrace.id)
        )
        return list(self.session.scalars(statement))
