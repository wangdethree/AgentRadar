"""收藏与忽略 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.search_session_repository import SearchSessionRepository
from app.schemas.interaction import (
    FavoriteCreate,
    FavoriteResponse,
    IgnoredRepositoryCreate,
    IgnoredRepositoryResponse,
)

router = APIRouter(tags=["收藏与忽略"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/favorites",
    response_model=FavoriteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="收藏仓库",
)
async def create_favorite(payload: FavoriteCreate, db: DatabaseSession) -> FavoriteResponse:
    """收藏已同步仓库，重复操作会更新备注。"""
    repository = RepositoryRepository(db).get_by_full_name(payload.full_name)
    if repository is None:
        raise HTTPException(status_code=404, detail="仓库尚未同步")
    if payload.source_session_id is not None:
        source_session = SearchSessionRepository(db).get(payload.source_session_id)
        if source_session is None:
            raise HTTPException(status_code=404, detail="来源搜索会话不存在")
    favorite = InteractionRepository(db).add_favorite(
        repository,
        note=payload.note,
        source_session_id=payload.source_session_id,
    )
    return FavoriteResponse.model_validate(favorite)


@router.get("/favorites", response_model=list[FavoriteResponse], summary="收藏列表")
async def list_favorites(db: DatabaseSession) -> list[FavoriteResponse]:
    """读取全部收藏及备注。"""
    return [
        FavoriteResponse.model_validate(item)
        for item in InteractionRepository(db).list_favorites()
    ]


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(favorite_id: int, db: DatabaseSession) -> Response:
    """删除一条收藏。"""
    if not InteractionRepository(db).delete_favorite(favorite_id):
        raise HTTPException(status_code=404, detail="收藏不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/ignored-repositories",
    response_model=IgnoredRepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="忽略仓库",
)
async def create_ignored_repository(
    payload: IgnoredRepositoryCreate,
    db: DatabaseSession,
) -> IgnoredRepositoryResponse:
    """添加忽略记录，后续搜索会在模型调用前移除该仓库。"""
    repository = RepositoryRepository(db).get_by_full_name(payload.full_name)
    if repository is None:
        raise HTTPException(status_code=404, detail="仓库尚未同步")
    ignored = InteractionRepository(db).add_ignored(repository, reason=payload.reason)
    return IgnoredRepositoryResponse.model_validate(ignored)


@router.get(
    "/ignored-repositories",
    response_model=list[IgnoredRepositoryResponse],
    summary="忽略列表",
)
async def list_ignored_repositories(db: DatabaseSession) -> list[IgnoredRepositoryResponse]:
    """读取全部忽略记录。"""
    return [
        IgnoredRepositoryResponse.model_validate(item)
        for item in InteractionRepository(db).list_ignored()
    ]


@router.delete(
    "/ignored-repositories/{ignored_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_ignored_repository(ignored_id: int, db: DatabaseSession) -> Response:
    """恢复一个被忽略的仓库。"""
    if not InteractionRepository(db).delete_ignored(ignored_id):
        raise HTTPException(status_code=404, detail="忽略记录不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
