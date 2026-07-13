"""收藏和忽略数据访问。"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.interaction import Favorite, IgnoredRepository
from app.models.repository import Repository


class InteractionRepository:
    """管理单用户收藏与忽略记录。"""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_favorite(
        self,
        repository: Repository,
        *,
        note: str | None,
        source_session_id: str | None,
    ) -> Favorite:
        """收藏已同步仓库；重复收藏时更新备注。"""
        favorite = self.session.scalar(
            select(Favorite).where(Favorite.repository_id == repository.id)
        )
        if favorite is None:
            favorite = Favorite(repository_id=repository.id)
            self.session.add(favorite)
        favorite.note = note
        favorite.source_session_id = source_session_id
        self.session.commit()
        self.session.refresh(favorite)
        return favorite

    def list_favorites(self) -> list[Favorite]:
        """按最近收藏时间返回列表。"""
        statement = (
            select(Favorite)
            .options(selectinload(Favorite.repository))
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        )
        return list(self.session.scalars(statement))

    def delete_favorite(self, favorite_id: int) -> bool:
        """删除收藏并返回是否存在。"""
        favorite = self.session.get(Favorite, favorite_id)
        if favorite is None:
            return False
        self.session.delete(favorite)
        self.session.commit()
        return True

    def add_ignored(self, repository: Repository, *, reason: str | None) -> IgnoredRepository:
        """忽略已同步仓库；重复操作时更新原因。"""
        ignored = self.session.scalar(
            select(IgnoredRepository).where(IgnoredRepository.repository_id == repository.id)
        )
        if ignored is None:
            ignored = IgnoredRepository(repository_id=repository.id)
            self.session.add(ignored)
        ignored.reason = reason
        self.session.commit()
        self.session.refresh(ignored)
        return ignored

    def list_ignored(self) -> list[IgnoredRepository]:
        """按最近忽略时间返回列表。"""
        statement = (
            select(IgnoredRepository)
            .options(selectinload(IgnoredRepository.repository))
            .order_by(IgnoredRepository.created_at.desc(), IgnoredRepository.id.desc())
        )
        return list(self.session.scalars(statement))

    def ignored_full_names(self) -> set[str]:
        """返回供确定性过滤使用的小写仓库名集合。"""
        statement = select(Repository.full_name).join(
            IgnoredRepository,
            IgnoredRepository.repository_id == Repository.id,
        )
        return {full_name.lower() for full_name in self.session.scalars(statement)}

    def delete_ignored(self, ignored_id: int) -> bool:
        """恢复被忽略项目并返回记录是否存在。"""
        ignored = self.session.get(IgnoredRepository, ignored_id)
        if ignored is None:
            return False
        self.session.delete(ignored)
        self.session.commit()
        return True

