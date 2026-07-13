"""GitHub 文件内容的解析工具。"""

import base64
import binascii
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.tools.github.errors import GitHubAPIError


class GitHubFileContent(BaseModel):
    """经过大小限制和 Base64 解码后的文件内容。"""

    model_config = ConfigDict(frozen=True)

    path: str
    sha: str
    size: int
    content: str
    html_url: str | None = None


def parse_file_content(payload: dict[str, Any], *, max_bytes: int) -> GitHubFileContent:
    """安全解码文本文件，拒绝超大文件和目录响应。"""
    if payload.get("type") != "file":
        raise GitHubAPIError("目标路径不是文件", code="github_content_not_file")
    size = int(payload.get("size", 0))
    if size > max_bytes:
        raise GitHubAPIError(
            f"文件超过读取上限 {max_bytes} 字节",
            code="github_content_too_large",
        )
    encoded_content = str(payload.get("content", "")).replace("\n", "")
    try:
        decoded = base64.b64decode(encoded_content, validate=True).decode("utf-8", errors="replace")
    except (binascii.Error, ValueError) as exc:
        raise GitHubAPIError(
            "GitHub 文件内容解码失败",
            code="github_content_decode_error",
        ) from exc
    return GitHubFileContent(
        path=str(payload.get("path", "")),
        sha=str(payload.get("sha", "")),
        size=size,
        content=decoded,
        html_url=str(payload["html_url"]) if payload.get("html_url") else None,
    )

