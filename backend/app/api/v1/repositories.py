"""仓库搜索与研究资料 API。"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_github_client
from app.core.database import get_db
from app.repositories.analysis_repository import AnalysisReportRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.analysis import ResearchReportData
from app.schemas.github import (
    RepositorySearchPage,
    RepositorySnapshotResponse,
    RepositorySummary,
)
from app.services.repository_service import RepositoryService
from app.services.research_service import ResearchService
from app.tools.github.client import GitHubClient
from app.tools.github.content import GitHubFileContent
from app.tools.github.readme import get_readme
from app.tools.github.tree import RepositoryTree, get_repository_tree

router = APIRouter(prefix="/repositories", tags=["GitHub 仓库"])

DatabaseSession = Annotated[Session, Depends(get_db)]
GitHubClientDependency = Annotated[GitHubClient, Depends(get_github_client)]


@router.get("/search", response_model=RepositorySearchPage, summary="搜索并保存候选仓库")
async def search_repository_candidates(
    db: DatabaseSession,
    github_client: GitHubClientDependency,
    q: Annotated[str, Query(min_length=1, max_length=256)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 30,
) -> RepositorySearchPage:
    """执行 GitHub 查询，并保存标准化仓库和指标快照。"""
    service = RepositoryService(db, github_client)
    return await service.search_and_persist(q, page=page, per_page=per_page)


@router.get("/{owner}/{repo}", response_model=RepositorySummary, summary="同步仓库详情")
async def sync_repository_detail(
    owner: str,
    repo: str,
    db: DatabaseSession,
    github_client: GitHubClientDependency,
) -> RepositorySummary:
    """读取 GitHub 最新详情并保存到本地数据库。"""
    service = RepositoryService(db, github_client)
    return await service.sync_repository(owner, repo)


@router.get("/{owner}/{repo}/readme", response_model=GitHubFileContent, summary="读取 README")
async def read_repository_readme(
    owner: str,
    repo: str,
    github_client: GitHubClientDependency,
    ref: str | None = None,
) -> GitHubFileContent:
    """读取并解码仓库 README。"""
    return await get_readme(github_client, owner, repo, ref=ref)


@router.get("/{owner}/{repo}/tree", response_model=RepositoryTree, summary="读取目录树")
async def read_repository_tree(
    owner: str,
    repo: str,
    github_client: GitHubClientDependency,
    ref: Annotated[str, Query(min_length=1)] = "main",
    depth: Annotated[int, Query(ge=0, le=10)] = 3,
) -> RepositoryTree:
    """按指定深度读取仓库目录树。"""
    return await get_repository_tree(github_client, owner, repo, ref, depth=depth)


@router.get(
    "/{owner}/{repo}/snapshots",
    response_model=list[RepositorySnapshotResponse],
    summary="读取仓库趋势快照",
)
async def get_repository_snapshots(
    owner: str,
    repo: str,
    db: DatabaseSession,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=2, le=1000)] = 500,
) -> list[RepositorySnapshotResponse]:
    """返回指定天数内的真实指标快照，不插值或补造缺失数据。"""
    store = RepositoryRepository(db)
    repository = store.get_by_full_name(f"{owner}/{repo}")
    if repository is None:
        raise HTTPException(status_code=404, detail="仓库尚未同步")
    snapshots = store.list_snapshots(
        repository.id,
        captured_after=datetime.now(UTC) - timedelta(days=days),
        limit=limit,
    )
    return [RepositorySnapshotResponse.model_validate(item) for item in snapshots]


@router.post(
    "/{owner}/{repo}/analyze",
    response_model=ResearchReportData,
    summary="分析单个仓库",
)
async def analyze_repository(
    owner: str,
    repo: str,
    db: DatabaseSession,
    github_client: GitHubClientDependency,
    report_type: Annotated[str, Query(pattern="^(shallow|deep)$")] = "deep",
) -> ResearchReportData:
    """同步仓库后执行浅层或深层证据化调查。"""
    repository = await RepositoryService(db, github_client).sync_repository(owner, repo)
    report = await ResearchService(github_client).research(
        repository,
        report_type=report_type,
    )
    AnalysisReportRepository(db).save(report)
    return report


@router.get(
    "/{owner}/{repo}/analysis",
    response_model=ResearchReportData,
    summary="读取最新分析报告",
)
async def get_repository_analysis(
    owner: str,
    repo: str,
    db: DatabaseSession,
    report_type: Annotated[str, Query(pattern="^(shallow|deep)$")] = "deep",
) -> ResearchReportData:
    """读取本地最新报告，不重复消耗 GitHub 配额。"""
    repository = RepositoryRepository(db).get_by_full_name(f"{owner}/{repo}")
    if repository is None:
        raise HTTPException(status_code=404, detail="仓库尚未同步")
    store = AnalysisReportRepository(db)
    record = store.get_latest(repository.id, report_type)
    if record is None:
        raise HTTPException(status_code=404, detail="分析报告不存在")
    return store.to_schema(record)
