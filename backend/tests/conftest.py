"""测试套件的公共配置。"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """项目运行时基于 asyncio，因此异步测试只执行该后端。"""
    return "asyncio"

