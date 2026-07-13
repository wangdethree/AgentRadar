"""APScheduler 生命周期配置。"""

from datetime import UTC, datetime
from typing import Any

from app.tasks.trending import collect_trending_snapshots


def start_trending_scheduler(interval_hours: int) -> Any:
    """启动单进程异步调度器；多副本部署时应迁移到独立 Worker。"""
    if interval_hours < 1:
        raise ValueError("热门项目采集间隔必须大于等于 1 小时")

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        collect_trending_snapshots,
        trigger="interval",
        hours=interval_hours,
        id="collect_trending_snapshots",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()
    return scheduler

