"""收藏和忽略 API 数据结构。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.github import RepositorySummary


class FavoriteCreate(BaseModel):
    """创建或更新收藏。"""

    full_name: str = Field(pattern=r"^[^/]+/[^/]+$", max_length=255)
    note: str | None = Field(default=None, max_length=2000)
    source_session_id: str | None = None


class FavoriteResponse(BaseModel):
    """收藏项目响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    note: str | None
    source_session_id: str | None
    created_at: datetime
    repository: RepositorySummary


class IgnoredRepositoryCreate(BaseModel):
    """创建或更新忽略记录。"""

    full_name: str = Field(pattern=r"^[^/]+/[^/]+$", max_length=255)
    reason: str | None = Field(default=None, max_length=500)


class IgnoredRepositoryResponse(BaseModel):
    """忽略项目响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reason: str | None
    created_at: datetime
    repository: RepositorySummary

