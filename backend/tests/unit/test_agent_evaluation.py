"""固定 Agent 评测集测试。"""

from pathlib import Path

from app.evaluation import evaluate_dataset, load_dataset


def test_agent_evaluation_baseline_meets_quality_thresholds() -> None:
    """离线评测应稳定覆盖需求、证据、过滤和推荐指标。"""
    dataset_path = Path(__file__).parents[2] / "evaluation" / "agent_cases.json"
    report = evaluate_dataset(load_dataset(dataset_path))

    assert report.requirement_case_count == 5
    assert report.research_case_count == 2
    assert report.requirement_field_accuracy == 1
    assert report.search_query_validity_rate == 1
    assert report.excluded_term_leakage_rate == 0
    assert report.capability_detection_accuracy >= 0.95
    assert report.wrapper_risk_accuracy == 1
    assert report.irrelevant_filter_recall == 1
    assert report.recommendation_precision_at_1 == 1
    assert report.reading_path_hallucination_rate == 0
    assert report.evidence_source_coverage_rate == 1
