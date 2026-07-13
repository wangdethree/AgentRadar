"""智能搜索会话 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.agents.graph import SearchWorkflow
from app.api.dependencies import get_github_client, get_llm_client
from app.core.database import get_db
from app.providers.llm import LLMClient
from app.repositories.search_session_repository import SearchSessionRepository
from app.schemas.search import (
    ExecutionTraceResponse,
    SearchExecutionResponse,
    SearchResultResponse,
    SearchSessionCreate,
    SearchSessionRefine,
    SearchSessionResponse,
)
from app.tools.github.client import GitHubClient

router = APIRouter(prefix="/search/sessions", tags=["智能搜索"])

DatabaseSession = Annotated[Session, Depends(get_db)]
GitHubClientDependency = Annotated[GitHubClient, Depends(get_github_client)]
LLMClientDependency = Annotated[LLMClient | None, Depends(get_llm_client)]


@router.post(
    "",
    response_model=SearchExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建并执行搜索会话",
)
async def create_search_session(
    payload: SearchSessionCreate,
    db: DatabaseSession,
    github_client: GitHubClientDependency,
    llm_client: LLMClientDependency,
) -> SearchExecutionResponse:
    """执行智能搜索基础链路，并返回最多五个研究目标。"""
    state = await SearchWorkflow(db, github_client, llm_client).run(payload.query)
    search_session = SearchSessionRepository(db).get(state["session_id"])
    if search_session is None:  # pragma: no cover - 工作流内部一致性保护
        raise HTTPException(status_code=500, detail="搜索会话保存失败")
    return SearchExecutionResponse(
        session=SearchSessionResponse.model_validate(search_session),
        discovered_count=len(state["discovered_repositories"]),
        filtered_count=len(state["filtered_repositories"]),
        screened_count=len(state["screened_repositories"]),
        research_targets=state["research_targets"],
        final_recommendations=state["final_recommendations"],
        llm_call_count=state["llm_call_count"],
        errors=state["errors"],
    )


@router.get("", response_model=list[SearchSessionResponse], summary="查看搜索历史")
async def list_search_sessions(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    session_status: Annotated[str | None, Query(alias="status", max_length=32)] = None,
) -> list[SearchSessionResponse]:
    """按时间倒序返回最近搜索，可按执行状态筛选。"""
    sessions = SearchSessionRepository(db).list_sessions(
        limit=limit,
        status=session_status,
    )
    return [SearchSessionResponse.model_validate(item) for item in sessions]


@router.get("/{session_id}", response_model=SearchSessionResponse, summary="查看搜索会话")
async def get_search_session(session_id: str, db: DatabaseSession) -> SearchSessionResponse:
    """读取搜索状态、结构化需求与搜索计划。"""
    search_session = SearchSessionRepository(db).get(session_id)
    if search_session is None:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    return SearchSessionResponse.model_validate(search_session)


@router.post(
    "/{session_id}/refine",
    response_model=SearchExecutionResponse,
    summary="继续筛选当前会话",
)
async def refine_search_session(
    session_id: str,
    payload: SearchSessionRefine,
    db: DatabaseSession,
    github_client: GitHubClientDependency,
    llm_client: LLMClientDependency,
) -> SearchExecutionResponse:
    """复用当前候选和已有分析报告，按追加条件重新推荐。"""
    store = SearchSessionRepository(db)
    if store.get(session_id) is None:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    state = await SearchWorkflow(db, github_client, llm_client).refine(
        session_id,
        payload.feedback,
    )
    search_session = store.get(session_id)
    if search_session is None:  # pragma: no cover - 内部一致性保护
        raise HTTPException(status_code=500, detail="搜索会话保存失败")
    return SearchExecutionResponse(
        session=SearchSessionResponse.model_validate(search_session),
        discovered_count=len(state["discovered_repositories"]),
        filtered_count=len(state["filtered_repositories"]),
        screened_count=len(state["screened_repositories"]),
        research_targets=state["research_targets"],
        final_recommendations=state["final_recommendations"],
        llm_call_count=state["llm_call_count"],
        errors=state["errors"],
    )


@router.get(
    "/{session_id}/results",
    response_model=list[SearchResultResponse],
    summary="查看阶段结果",
)
async def get_search_results(
    session_id: str,
    db: DatabaseSession,
    stage: Annotated[str | None, Query()] = None,
) -> list[SearchResultResponse]:
    """读取初筛或研究目标结果，默认返回全部阶段。"""
    store = SearchSessionRepository(db)
    if store.get(session_id) is None:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    results = store.list_results(session_id, stage)
    return [SearchResultResponse.model_validate(item) for item in results]


@router.get(
    "/{session_id}/traces",
    response_model=list[ExecutionTraceResponse],
    summary="查看执行轨迹",
)
async def get_search_traces(
    session_id: str,
    db: DatabaseSession,
) -> list[ExecutionTraceResponse]:
    """返回节点耗时、输入输出摘要和工具名称，不暴露模型思维过程。"""
    store = SearchSessionRepository(db)
    if store.get(session_id) is None:
        raise HTTPException(status_code=404, detail="搜索会话不存在")
    return [ExecutionTraceResponse.model_validate(item) for item in store.list_traces(session_id)]
