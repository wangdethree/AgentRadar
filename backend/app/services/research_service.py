"""仓库资料采集与证据化规则分析。"""

from contextlib import suppress

from app.schemas.analysis import (
    AgentCapabilities,
    EngineeringAnalysis,
    EvidenceItem,
    ReadingPathItem,
    ResearchReportData,
)
from app.schemas.github import RepositorySummary
from app.tools.github.client import GitHubClient
from app.tools.github.content import GitHubFileContent
from app.tools.github.errors import GitHubAPIError
from app.tools.github.issues import get_issues
from app.tools.github.readme import get_readme
from app.tools.github.releases import get_releases
from app.tools.github.repository import get_file_content
from app.tools.github.tree import RepositoryTree, RepositoryTreeEntry, get_repository_tree

DEPENDENCY_FILE_NAMES = {
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "poetry.lock",
    "uv.lock",
}


class ResearchService:
    """按调查等级读取有限资料，单项失败不会中断整个报告。"""

    def __init__(self, github_client: GitHubClient) -> None:
        self.github_client = github_client

    async def research(
        self,
        repository: RepositorySummary,
        *,
        report_type: str,
    ) -> ResearchReportData:
        """采集 README、目录、依赖；深度模式额外读取 Release 和 Issue。"""
        readme: GitHubFileContent | None = None
        tree = RepositoryTree()
        dependency_files: list[GitHubFileContent] = []
        release_count = 0
        issue_count = 0

        with suppress(GitHubAPIError):
            readme = await get_readme(
                self.github_client,
                repository.owner,
                repository.name,
                ref=repository.default_branch,
            )
        with suppress(GitHubAPIError):
            tree = await get_repository_tree(
                self.github_client,
                repository.owner,
                repository.name,
                repository.default_branch,
                depth=4 if report_type == "deep" else 2,
            )

        dependency_paths = [
            entry.path
            for entry in tree.entries
            if entry.path.rsplit("/", maxsplit=1)[-1].lower() in DEPENDENCY_FILE_NAMES
        ][:3]
        for path in dependency_paths:
            try:
                dependency_files.append(
                    await get_file_content(
                        self.github_client,
                        repository.owner,
                        repository.name,
                        path,
                        ref=repository.default_branch,
                        max_bytes=150_000,
                    )
                )
            except GitHubAPIError:
                continue

        if report_type == "deep":
            with suppress(GitHubAPIError):
                release_count = len(
                    await get_releases(
                        self.github_client, repository.owner, repository.name, limit=5
                    )
                )
            with suppress(GitHubAPIError):
                issue_count = len(
                    await get_issues(
                        self.github_client, repository.owner, repository.name, limit=10
                    )
                )

        return build_research_report(
            repository,
            report_type=report_type,
            readme=readme,
            tree=tree,
            dependency_files=dependency_files,
            release_count=release_count,
            issue_count=issue_count,
        )


def build_research_report(
    repository: RepositorySummary,
    *,
    report_type: str,
    readme: GitHubFileContent | None,
    tree: RepositoryTree,
    dependency_files: list[GitHubFileContent],
    release_count: int = 0,
    issue_count: int = 0,
) -> ResearchReportData:
    """仅依据已读取证据生成分析，不虚构文件或能力。"""
    paths = [entry.path for entry in tree.entries]
    combined_text = "\n".join(
        [
            repository.name,
            repository.description or "",
            readme.content[:80_000] if readme else "",
            *paths,
            *(item.content[:30_000] for item in dependency_files),
        ]
    ).lower()
    capabilities = AgentCapabilities(
        tool_calling=_contains_any(
            combined_text, ("tool calling", "bind_tools", "tools/", "toolnode")
        ),
        state_management=_contains_any(
            combined_text, ("stategraph", "state management", "state.py")
        ),
        workflow_orchestration=_contains_any(combined_text, ("langgraph", "workflow", "graph/")),
        multi_round_execution=_contains_any(
            combined_text, ("agent loop", "while ", "multi-turn", "multiturn")
        ),
        memory=_contains_any(combined_text, ("memory", "checkpointer", "checkpoint")),
        human_in_the_loop=_contains_any(
            combined_text, ("human-in-the-loop", "interrupt_before", "interrupt(")
        ),
        persistence=_contains_any(
            combined_text, ("postgres", "sqlite", "database", "checkpointer")
        ),
        evaluation=_contains_any(combined_text, ("evaluation", "evals/", "agent_eval")),
    )
    lower_paths = [path.lower() for path in paths]
    dependency_paths = [item.path for item in dependency_files]
    engineering = EngineeringAnalysis(
        has_api=any("api" in path or "fastapi" in path for path in lower_paths),
        has_tests=any(path.startswith("test") or "/test" in path for path in lower_paths),
        has_docker=any("dockerfile" in path or "docker-compose" in path for path in lower_paths),
        has_database=_contains_any(combined_text, ("sqlalchemy", "postgres", "sqlite", "database")),
        has_configuration=any(
            path.endswith((".toml", ".yaml", ".yml", ".env.example")) for path in lower_paths
        ),
        has_documentation=readme is not None
        or any(path.startswith("docs/") for path in lower_paths),
        dependency_files=dependency_paths,
        file_count=len([entry for entry in tree.entries if entry.type == "blob"]),
    )
    evidence = _build_evidence(
        readme,
        tree,
        dependency_files,
        release_count=release_count,
        issue_count=issue_count,
    )
    reading_path = _build_reading_path(tree.entries)
    wrapper_risk = _calculate_wrapper_risk(combined_text, capabilities, engineering)
    strengths = _build_strengths(capabilities, engineering, release_count)
    weaknesses = _build_weaknesses(capabilities, engineering, readme)
    summary = _extract_summary(readme, repository)
    return ResearchReportData(
        repository=repository,
        report_type="deep" if report_type == "deep" else "shallow",
        project_summary=summary,
        agent_capabilities=capabilities,
        engineering_analysis=engineering,
        strengths=strengths,
        weaknesses=weaknesses,
        evidence=evidence,
        reading_path=reading_path,
        wrapper_risk=wrapper_risk,
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _extract_summary(
    readme: GitHubFileContent | None,
    repository: RepositorySummary,
) -> str:
    """优先使用 README 首个正文句，缺失时退回仓库描述。"""
    if readme:
        for line in readme.content.splitlines():
            cleaned = line.strip().lstrip("#").strip()
            if cleaned and not cleaned.startswith(("!", "[", "<")) and len(cleaned) >= 20:
                return cleaned[:500]
    return repository.description or f"{repository.full_name} 的 AI Agent 项目"


def _build_evidence(
    readme: GitHubFileContent | None,
    tree: RepositoryTree,
    dependencies: list[GitHubFileContent],
    *,
    release_count: int,
    issue_count: int,
) -> list[EvidenceItem]:
    evidence: list[EvidenceItem] = []
    if readme:
        evidence.append(
            EvidenceItem(source="readme", path=readme.path, observation="已读取项目说明")
        )
    evidence.append(
        EvidenceItem(
            source="tree",
            observation=f"已读取 {len(tree.entries)} 个目录项，截断状态：{tree.truncated}",
        )
    )
    evidence.extend(
        EvidenceItem(source="dependency", path=item.path, observation="已读取依赖或工程配置")
        for item in dependencies
    )
    if release_count:
        evidence.append(
            EvidenceItem(source="release", observation=f"读取最近 {release_count} 个版本")
        )
    if issue_count:
        evidence.append(
            EvidenceItem(source="issue", observation=f"读取最近 {issue_count} 个 Issue")
        )
    return evidence


def _build_reading_path(entries: list[RepositoryTreeEntry]) -> list[ReadingPathItem]:
    """只从真实目录项选择阅读路径。"""
    candidates: list[tuple[int, str, str]] = []
    for entry in entries:
        if entry.type != "blob":
            continue
        path = entry.path.lower()
        if path.endswith(("main.py", "app.py", "__main__.py")):
            candidates.append((0, entry.path, "理解应用入口与初始化流程"))
        elif "graph" in path and path.endswith(".py"):
            candidates.append((1, entry.path, "理解 Agent 图结构与工作流编排"))
        elif "state" in path and path.endswith(".py"):
            candidates.append((2, entry.path, "查看 Agent 状态结构"))
        elif "node" in path and path.endswith(".py"):
            candidates.append((3, entry.path, "理解节点职责与状态流转"))
        elif "tool" in path and path.endswith(".py"):
            candidates.append((4, entry.path, "查看工具注册、参数和异常处理"))
        elif "api" in path and path.endswith(".py"):
            candidates.append((5, entry.path, "了解 Agent 如何封装为接口"))
        elif path.startswith("test") or "/test" in path:
            candidates.append((6, entry.path, "查看项目如何验证核心行为"))

    seen: set[str] = set()
    reading_path: list[ReadingPathItem] = []
    for _, path, reason in sorted(candidates):
        if path in seen:
            continue
        seen.add(path)
        reading_path.append(ReadingPathItem(path=path, reason=reason))
        if len(reading_path) >= 8:
            break
    return reading_path


def _calculate_wrapper_risk(
    text: str,
    capabilities: AgentCapabilities,
    engineering: EngineeringAnalysis,
) -> str:
    capability_count = sum(capabilities.model_dump().values())
    simple_ui = "streamlit" in text or "gradio" in text
    if (
        simple_ui
        and capability_count <= 1
        and not engineering.has_tests
        and not engineering.has_api
    ):
        return "high"
    if capability_count <= 2 or (not engineering.has_tests and not engineering.has_api):
        return "medium"
    return "low"


def _build_strengths(
    capabilities: AgentCapabilities,
    engineering: EngineeringAnalysis,
    release_count: int,
) -> list[str]:
    strengths: list[str] = []
    capability_count = sum(capabilities.model_dump().values())
    if capability_count >= 5:
        strengths.append("Agent 能力覆盖较完整")
    if capabilities.tool_calling and capabilities.state_management:
        strengths.append("同时具备工具调用与状态管理证据")
    if engineering.has_api and engineering.has_tests:
        strengths.append("包含 API 与测试，工程闭环较完整")
    if engineering.has_docker:
        strengths.append("提供容器化配置，便于部署和演示")
    if release_count:
        strengths.append("存在近期 Release 记录")
    return strengths or ["仓库结构和说明可供进一步研究"]


def _build_weaknesses(
    capabilities: AgentCapabilities,
    engineering: EngineeringAnalysis,
    readme: GitHubFileContent | None,
) -> list[str]:
    weaknesses: list[str] = []
    if not capabilities.memory:
        weaknesses.append("未发现明确的 Memory 或 Checkpoint 证据")
    if not capabilities.evaluation:
        weaknesses.append("未发现 Agent Evaluation 相关实现")
    if not engineering.has_tests:
        weaknesses.append("未发现测试目录或测试文件")
    if not engineering.has_docker:
        weaknesses.append("未发现容器化配置")
    if readme is None:
        weaknesses.append("README 读取失败或不存在")
    return weaknesses
