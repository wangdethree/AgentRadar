"""系统健康检查接口。"""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["系统状态"])


@router.get("/health", response_model=HealthResponse, summary="API 健康检查")
async def health_check() -> HealthResponse:
    """返回轻量健康状态，不访问外部服务。"""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version="0.1.0")

