"""GitHub 文件内容解析测试。"""

import base64

import pytest

from app.tools.github.content import parse_file_content
from app.tools.github.errors import GitHubAPIError


def test_parse_file_content_decodes_base64() -> None:
    """文本文件应正确解码并保留证据路径。"""
    raw = "# Agent\n中文说明"
    result = parse_file_content(
        {
            "type": "file",
            "path": "README.md",
            "sha": "abc",
            "size": len(raw.encode()),
            "content": base64.b64encode(raw.encode()).decode(),
            "html_url": "https://github.com/example/agent/blob/main/README.md",
        },
        max_bytes=100,
    )

    assert result.content == raw
    assert result.path == "README.md"


def test_parse_file_content_rejects_large_file() -> None:
    """超大文件不应进入模型上下文。"""
    with pytest.raises(GitHubAPIError) as error:
        parse_file_content(
            {"type": "file", "path": "large.txt", "sha": "abc", "size": 101},
            max_bytes=100,
        )

    assert error.value.code == "github_content_too_large"

