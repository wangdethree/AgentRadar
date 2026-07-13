"""统一注册版本化 API 路由。"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.repositories import router as repositories_router
from app.api.v1.search import router as search_router
from app.api.v1.trending import router as trending_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(repositories_router)
api_router.include_router(search_router)
api_router.include_router(trending_router)
