"""热门项目雷达 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.trending import TrendingCard
from app.services.trend_service import CATEGORIES, TrendService

router = APIRouter(prefix="/trending", tags=["热门项目雷达"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _list_cards(
    db: Session,
    kind: str,
    limit: int,
    category: str | None,
    include_demo: bool,
) -> list[TrendingCard]:
    """复用三类榜单的查询逻辑。"""
    return TrendService(db).list_cards(
        kind,
        limit=limit,
        category=category,
        include_demo=include_demo,
    )


@router.get("/daily", response_model=list[TrendingCard], summary="今日热门")
async def get_daily_trending(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    include_demo: bool = False,
) -> list[TrendingCard]:
    """按最近 24 小时 Star 增量和综合趋势分排序。"""
    return _list_cards(db, "daily", limit, category, include_demo)


@router.get("/weekly", response_model=list[TrendingCard], summary="本周上升")
async def get_weekly_trending(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    include_demo: bool = False,
) -> list[TrendingCard]:
    """按最近 7 天增长和综合趋势分排序。"""
    return _list_cards(db, "weekly", limit, category, include_demo)


@router.get("/potential", response_model=list[TrendingCard], summary="新项目潜力")
async def get_potential_trending(
    db: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    category: str | None = None,
    include_demo: bool = False,
) -> list[TrendingCard]:
    """展示创建不超过一年且总 Star 不高的增长项目。"""
    return _list_cards(db, "potential", limit, category, include_demo)


@router.get("/categories", response_model=list[str], summary="热门项目分类")
async def get_trending_categories() -> list[str]:
    """返回 V1 支持的项目分类。"""
    return list(CATEGORIES)

