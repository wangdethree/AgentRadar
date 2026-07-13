"""健康检查响应结构。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """健康检查的稳定响应格式。"""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
    service: str
    version: str

