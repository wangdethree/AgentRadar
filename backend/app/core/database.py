"""数据库引擎、会话与 FastAPI 依赖。"""

from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models import Base


def create_database_engine(database_url: str) -> Engine:
    """创建数据库引擎，并处理 SQLite 的多线程测试配置。"""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args, pool_pre_ping=True)


engine = create_database_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database(database_engine: Engine = engine) -> None:
    """开发阶段创建数据表；正式迁移由 Alembic 接管。"""
    Base.metadata.create_all(bind=database_engine)


def get_db() -> Generator[Session, None, None]:
    """为每个请求提供独立数据库会话并确保关闭。"""
    with SessionLocal() as session:
        yield session

