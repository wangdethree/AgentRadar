"""仓库搜索与研究资料 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_github_client
from app.core.database import get_db
from app.schemas.github import RepositorySearchPage, RepositorySummary
from app.services.repository_service import RepositoryService
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

