"""内存缓存服务测试。"""

import pytest

from app.services.cache_service import AsyncTTLCache


@pytest.mark.anyio
async def test_cache_set_get_and_clear() -> None:
    """缓存应支持写入、命中和清空。"""
    cache: AsyncTTLCache[dict[str, int]] = AsyncTTLCache(default_ttl_seconds=60)

    await cache.set("key", {"value": 1})
    assert await cache.get("key") == {"value": 1}

    await cache.clear()
    assert await cache.get("key") is None


def test_cache_rejects_invalid_ttl() -> None:
    """非正有效期属于配置错误，应立即暴露。"""
    with pytest.raises(ValueError, match="必须大于 0"):
        AsyncTTLCache[object](default_ttl_seconds=0)
