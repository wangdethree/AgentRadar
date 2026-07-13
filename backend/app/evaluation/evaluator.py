"""使用固定数据评估需求解析、研究证据和推荐稳定性。"""

from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.schemas import AgentEvaluationDataset, AgentEvaluationReport
from app.schemas.analysis import ResearchReportData
from app.services.filter_service import normalize_and_filter, screen_candidates
from app.services.requirement_service import build_search_plan, parse_requirement
from app.services.research_service import build_research_report
from app.services.scoring_service import build_recommendations
from app.tools.github.content import GitHubFileContent
from app.tools.github.tree import RepositoryTree, RepositoryTreeEntry

REQUIREMENT_FIELDS = (
    "topics",
    "languages",
    "preferred_technologies",
    "required_capabilities",
    "difficulty",
    "goal",
    "excluded_features",
)


def load_dataset(path: Path) -> AgentEvaluationDataset:
    """读取并校验版本化 JSON 评测集。"""
    return AgentEvaluationDataset.model_validate_json(path.read_text(encoding="utf-8"))


def _ratio(passed: int, total: int) -> float:
    """统一处理空分母并保留四位小数。"""
    return round(passed / total, 4) if total else 1.0


def _build_reports(dataset: AgentEvaluationDataset) -> list[ResearchReportData]:
    """把固定 README 和目录树转换为真实研究服务输出。"""
    reports: list[ResearchReportData] = []
    for case in dataset.research_cases:
        readme = GitHubFileContent(
            path=case.readme_path,
            sha=f"{case.id}-readme",
            size=len(case.readme_content.encode()),
            content=case.readme_content,
        )
        entries = [
            RepositoryTreeEntry(path=path, type="blob", sha=f"{case.id}-{index}", size=100)
            for index, path in enumerate(case.tree_paths)
        ]
        dependencies = [
            GitHubFileContent(
                path=path,
                sha=f"{case.id}-dependency-{index}",
                size=len(content.encode()),
                content=content,
            )
            for index, (path, content) in enumerate(case.dependency_files.items())
        ]
        reports.append(
            build_research_report(
                case.repository,
                report_type="deep",
                readme=readme,
                tree=RepositoryTree(entries=entries),
                dependency_files=dependencies,
                release_count=1,
                issue_count=2,
            )
        )
    return reports


def _evaluate_requirements(dataset: AgentEvaluationDataset) -> tuple[float, float, float]:
    """计算字段准确率、查询有效率和排除词泄漏率。"""
    matched_fields = 0
    total_fields = len(dataset.requirement_cases) * len(REQUIREMENT_FIELDS)
    valid_plans = 0
    excluded_case_count = 0
    leaking_case_count = 0
    fixed_now = datetime(2026, 7, 13, tzinfo=UTC)

    for case in dataset.requirement_cases:
        actual = parse_requirement(case.query)
        for field in REQUIREMENT_FIELDS:
            if getattr(actual, field) == getattr(case.expected, field):
                matched_fields += 1

        plan = build_search_plan(actual, now=fixed_now)
        queries = [item.query for item in plan.queries]
        qualifiers_valid = all(
            "fork:false" in query and "archived:false" in query and "pushed:>=" in query
            for query in queries
        )
        language_valid = not actual.languages or all(
            f"language:{actual.languages[0]}" in query for query in queries
        )
        if 3 <= len(queries) <= 5 and qualifiers_valid and language_valid:
            valid_plans += 1

        if actual.excluded_features:
            excluded_case_count += 1
            lowered_queries = " ".join(queries).lower()
            if any(feature.lower() in lowered_queries for feature in actual.excluded_features):
                leaking_case_count += 1

    return (
        _ratio(matched_fields, total_fields),
        _ratio(valid_plans, len(dataset.requirement_cases)),
        _ratio(leaking_case_count, excluded_case_count),
    )


def _evaluate_research(
    dataset: AgentEvaluationDataset,
    reports: list[ResearchReportData],
) -> tuple[float, float, float, float]:
    """评估能力、套壳风险、阅读路径和证据来源。"""
    capability_matches = 0
    capability_total = 0
    wrapper_matches = 0
    invalid_paths = 0
    reading_path_total = 0
    covered_sources = 0
    expected_sources = 0

    for case, report in zip(dataset.research_cases, reports, strict=True):
        actual_capabilities = report.agent_capabilities.model_dump()
        expected_capabilities = case.expected_capabilities.model_dump()
        for name, expected in expected_capabilities.items():
            capability_total += 1
            if actual_capabilities[name] == expected:
                capability_matches += 1
        if report.wrapper_risk == case.expected_wrapper_risk:
            wrapper_matches += 1

        real_paths = set(case.tree_paths)
        for item in report.reading_path:
            reading_path_total += 1
            if item.path not in real_paths:
                invalid_paths += 1

        actual_sources = {item.source for item in report.evidence}
        for source in case.expected_evidence_sources:
            expected_sources += 1
            if source in actual_sources:
                covered_sources += 1

    return (
        _ratio(capability_matches, capability_total),
        _ratio(wrapper_matches, len(reports)),
        _ratio(invalid_paths, reading_path_total),
        _ratio(covered_sources, expected_sources),
    )


def _evaluate_filtering(dataset: AgentEvaluationDataset) -> float:
    """验证 fork、归档、无 README、过旧、忽略和重复过滤。"""
    reference = dataset.research_cases[0].repository
    ignored = dataset.research_cases[-1].repository
    stale_time = datetime(2023, 1, 1, tzinfo=UTC)
    candidates = [
        reference,
        reference,
        reference.model_copy(
            update={"github_id": 9101, "full_name": "fixture/fork", "is_fork": True}
        ),
        reference.model_copy(
            update={"github_id": 9102, "full_name": "fixture/archived", "is_archived": True}
        ),
        reference.model_copy(
            update={"github_id": 9103, "full_name": "fixture/no-readme", "has_readme": False}
        ),
        reference.model_copy(
            update={
                "github_id": 9104,
                "full_name": "fixture/stale",
                "github_updated_at": stale_time,
                "pushed_at": stale_time,
            }
        ),
        ignored,
    ]
    outcome = normalize_and_filter(
        candidates,
        ignored_full_names={ignored.full_name},
        updated_after=datetime(2025, 1, 1, tzinfo=UTC),
    )
    removed_total = sum(outcome.removed_counts.values())
    return _ratio(removed_total, len(candidates) - 1)


def _evaluate_recommendation(
    dataset: AgentEvaluationDataset,
    reports: list[ResearchReportData],
) -> float:
    """用统一需求验证期望相关仓库是否排在第一位。"""
    requirement = parse_requirement(
        "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理，适合简历"
    )
    screened = screen_candidates(
        [case.repository for case in dataset.research_cases],
        requirement,
    )
    recommendations = build_recommendations(screened, reports, requirement)
    if not recommendations:
        return 0.0
    return float(recommendations[0].repository.full_name == dataset.expected_top_repository)


def evaluate_dataset(dataset: AgentEvaluationDataset) -> AgentEvaluationReport:
    """执行完整离线基线评测。"""
    requirement_accuracy, query_validity, exclusion_leakage = _evaluate_requirements(dataset)
    reports = _build_reports(dataset)
    capability_accuracy, wrapper_accuracy, path_hallucination, evidence_coverage = (
        _evaluate_research(dataset, reports)
    )
    return AgentEvaluationReport(
        dataset_version=dataset.version,
        requirement_case_count=len(dataset.requirement_cases),
        research_case_count=len(dataset.research_cases),
        requirement_field_accuracy=requirement_accuracy,
        search_query_validity_rate=query_validity,
        excluded_term_leakage_rate=exclusion_leakage,
        capability_detection_accuracy=capability_accuracy,
        wrapper_risk_accuracy=wrapper_accuracy,
        irrelevant_filter_recall=_evaluate_filtering(dataset),
        recommendation_precision_at_1=_evaluate_recommendation(dataset, reports),
        reading_path_hallucination_rate=path_hallucination,
        evidence_source_coverage_rate=evidence_coverage,
    )
