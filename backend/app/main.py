"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.health import health_check
from app.core.config import get_settings
from app.core.database import init_database
from app.core.exception_handlers import register_exception_handlers
from app.schemas.health import HealthResponse


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """初始化数据库，并按配置启动热门仓库采集。"""
    init_database()
    settings = get_settings()
    scheduler: Any | None = None
    if settings.trending_scheduler_enabled:
        from app.tasks.scheduler import start_trending_scheduler

        scheduler = start_trending_scheduler(settings.trending_collection_interval_hours)
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用，便于测试和后续扩展。"""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        description="GitHub AI Agent 项目发现、趋势分析与深度研究服务",
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_v1_prefix)
    register_exception_handlers(application)
    application.add_api_route(
        "/health",
        health_check,
        methods=["GET"],
        response_model=HealthResponse,
        tags=["系统状态"],
        summary="根健康检查",
    )
    return application


app = create_app()
