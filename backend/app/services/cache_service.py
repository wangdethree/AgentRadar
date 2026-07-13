"""轻量异步内存缓存，后续可替换为 Redis。"""

import asyncio
from dataclasses import dataclass
from time import monotonic
from typing import Generic, TypeVar

ValueT = TypeVar("ValueT")


@dataclass(frozen=True, slots=True)
class CacheEntry(Generic[ValueT]):
    """缓存值及其过期时间。"""

    value: ValueT
    expires_at: float


class AsyncTTLCache(Generic[ValueT]):
    """进程内 TTL 缓存，使用锁保护并发读写。"""

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("缓存有效期必须大于 0")
        self.default_ttl_seconds = default_ttl_seconds
        self._entries: dict[str, CacheEntry[ValueT]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ValueT | None:
        """读取未过期的值，并顺便清理已过期条目。"""
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._entries.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: ValueT, ttl_seconds: int | None = None) -> None:
        """写入缓存，可为单个条目覆盖默认有效期。"""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        if ttl <= 0:
            raise ValueError("缓存有效期必须大于 0")
        async with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=monotonic() + ttl)

    async def delete(self, key: str) -> None:
        """删除单个缓存条目。"""
        async with self._lock:
            self._entries.pop(key, None)

    async def clear(self) -> None:
        """清空当前进程的全部缓存。"""
        async with self._lock:
            self._entries.clear()

