"""GitHub README 读取工具。"""

from app.tools.github.client import GitHubClient
from app.tools.github.content import GitHubFileContent, parse_file_content


async def get_readme(
    client: GitHubClient,
    owner: str,
    repo: str,
    *,
    ref: str | None = None,
    max_bytes: int = 300_000,
) -> GitHubFileContent:
    """读取仓库 README，并限制输入模型的文本体积。"""
    params = {"ref": ref} if ref else None
    payload = await client.get_json(f"/repos/{owner}/{repo}/readme", params=params)
    return parse_file_content(payload, max_bytes=max_bytes)

