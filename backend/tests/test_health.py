"""健康检查接口测试。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_health_check() -> None:
    """根健康检查应便于容器和负载均衡器探测。"""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "AgentRadar",
        "version": "0.1.0",
    }


def test_versioned_health_check() -> None:
    """版本化健康检查应供前端统一 API 客户端调用。"""
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

