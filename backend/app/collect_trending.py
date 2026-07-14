"""手动执行一次真实 GitHub 热门仓库快照采集。"""

import asyncio
import json

from app.tasks.trending import collect_trending_snapshots


def main() -> None:
    """运行固定主题采集，并输出适合排查的结构化结果。"""
    result = asyncio.run(collect_trending_snapshots())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["repository_count"] == 0 and result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
