"""命令行运行 Agent 离线评测。"""

import argparse
from pathlib import Path

from app.evaluation.evaluator import evaluate_dataset, load_dataset
from app.evaluation.schemas import AgentEvaluationReport

METRIC_LABELS = {
    "requirement_field_accuracy": "条件字段准确率",
    "search_query_validity_rate": "搜索查询有效率",
    "excluded_term_leakage_rate": "排除词查询泄漏率",
    "capability_detection_accuracy": "Agent 能力识别准确率",
    "wrapper_risk_accuracy": "套壳风险判断准确率",
    "irrelevant_filter_recall": "错误项目过滤召回率",
    "recommendation_precision_at_1": "首位推荐准确率",
    "reading_path_hallucination_rate": "不存在文件路径幻觉率",
    "evidence_source_coverage_rate": "证据来源覆盖率",
}


def _to_markdown(report: AgentEvaluationReport) -> str:
    """生成可直接放入项目文档的评测表。"""
    values = report.model_dump()
    lines = [
        "# AgentRadar Agent 离线评测结果",
        "",
        f"- 数据集版本：`{report.dataset_version}`",
        f"- 评测模式：`{report.evaluation_mode}`",
        f"- 需求用例：{report.requirement_case_count}",
        f"- 仓库研究用例：{report.research_case_count}",
        "",
        "| 指标 | 结果 |",
        "|---|---:|",
    ]
    for field, label in METRIC_LABELS.items():
        lines.append(f"| {label} | {float(values[field]):.2%} |")
    lines.extend(
        [
            "",
            "> 该基线完全离线运行，不产生 GitHub 工具调用或模型费用。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    """解析参数并输出 JSON 或 Markdown。"""
    parser = argparse.ArgumentParser(description="运行 AgentRadar 固定 Agent 评测集")
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        default=Path("evaluation/agent_cases.json"),
        help="评测集 JSON 路径",
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args()
    report = evaluate_dataset(load_dataset(args.dataset))
    if args.format == "markdown":
        print(_to_markdown(report))
    else:
        print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
