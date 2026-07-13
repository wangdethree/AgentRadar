"""GitHub 工具的统一错误结构。"""

from dataclasses import dataclass


@dataclass(eq=False)
class GitHubAPIError(Exception):
    """可安全记录和返回给工作流的 GitHub API 错误。"""

    message: str
    code: str = "github_api_error"
    status_code: int | None = None
    retryable: bool = False
    rate_limit_reset: int | None = None

    def __str__(self) -> str:
        return self.message


class GitHubAuthenticationError(GitHubAPIError):
    """Token 缺失权限、无效或过期。"""


class GitHubNotFoundError(GitHubAPIError):
    """仓库或资源不存在。"""


class GitHubRateLimitError(GitHubAPIError):
    """GitHub API 额度已耗尽或触发二级限流。"""


class GitHubTimeoutError(GitHubAPIError):
    """请求在规定时间内未完成。"""


class GitHubTransportError(GitHubAPIError):
    """DNS、连接等传输层故障。"""


class GitHubServerError(GitHubAPIError):
    """GitHub 服务器暂时不可用。"""

