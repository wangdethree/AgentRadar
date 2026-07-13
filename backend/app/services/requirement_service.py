"""自然语言需求的低成本结构化与搜索计划生成。"""

import re
from datetime import UTC, datetime, timedelta

from app.schemas.search import ParsedRequirement, SearchPlan, SearchQuery

TERM_GROUPS: dict[str, tuple[str, ...]] = {
    "LangGraph": ("langgraph",),
    "MCP": ("mcp", "model context protocol"),
    "Multi-Agent": ("multi-agent", "multi agent", "多智能体", "多 agent"),
    "Agent Memory": ("agent memory", "长期记忆", "记忆能力", "memory"),
    "Agent Evaluation": ("agent evaluation", "agent eval", "智能体评测", "评测"),
    "Browser Agent": ("browser agent", "浏览器 agent"),
    "Coding Agent": ("coding agent", "代码 agent", "编程 agent"),
    "Research Agent": ("research agent", "研究 agent"),
    "RAG Agent": ("rag agent", "rag"),
}

LANGUAGE_GROUPS: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "TypeScript": ("typescript", "ts 项目", "ts工程"),
    "JavaScript": ("javascript", "js 项目", "js工程"),
    "Java": ("java",),
    "Go": ("golang", "go 项目", "go工程"),
}

TECHNOLOGY_GROUPS: dict[str, tuple[str, ...]] = {
    "FastAPI": ("fastapi",),
    "LangGraph": ("langgraph",),
    "CrewAI": ("crewai",),
    "AutoGen": ("autogen",),
    "Docker": ("docker",),
    "React": ("react",),
}

CAPABILITY_GROUPS: dict[str, tuple[str, ...]] = {
    "tool calling": ("tool calling", "工具调用", "调用工具"),
    "state management": ("state management", "状态管理"),
    "memory": ("memory", "长期记忆", "记忆能力"),
    "human-in-the-loop": ("human-in-the-loop", "human in the loop", "人工介入"),
    "multi-agent": ("multi-agent", "multi agent", "多智能体", "多 agent"),
    "evaluation": ("evaluation", "评测", "评估"),
    "persistence": ("persistence", "持久化"),
}


def _detect_terms(query: str, groups: dict[str, tuple[str, ...]]) -> list[str]:
    """按定义顺序提取术语，保证输出稳定可测试。"""
    lowered = query.lower()
    return [name for name, aliases in groups.items() if any(alias in lowered for alias in aliases)]


def _detect_exclusions(query: str) -> list[str]:
    """只把明确位于否定词后的已知特征识别为排除项。"""
    exclusions: list[str] = []
    groups = {**TECHNOLOGY_GROUPS, "simple chatbot": ("简单聊天", "聊天套壳", "simple chatbot")}
    for name, aliases in groups.items():
        for alias in aliases:
            pattern = rf"(?:不要|排除|避免|不想要|without|exclude)\s*{re.escape(alias)}"
            if re.search(pattern, query, flags=re.IGNORECASE):
                exclusions.append(name)
                break
    return exclusions


def parse_requirement(user_query: str) -> ParsedRequirement:
    """使用确定性规则提取常见技术条件，后续可由 LLM Provider 增强。"""
    query = user_query.strip()
    if len(query) < 3:
        raise ValueError("搜索需求至少需要 3 个字符")
    lowered = query.lower()

    if any(term in lowered for term in ("初学", "入门", "beginner", "简单")):
        difficulty = "beginner"
    elif any(term in lowered for term in ("高级", "复杂", "advanced")):
        difficulty = "advanced"
    elif any(term in lowered for term in ("中等", "intermediate", "不要太高")):
        difficulty = "intermediate"
    else:
        difficulty = "any"

    if any(term in lowered for term in ("简历", "面试", "求职", "resume")):
        goal = "resume_project"
    elif any(term in lowered for term in ("二次开发", "改造", "secondary development")):
        goal = "secondary_development"
    elif any(term in lowered for term in ("参考", "借鉴", "reference")):
        goal = "reference"
    else:
        goal = "learn"

    topics = _detect_terms(query, TERM_GROUPS)
    return ParsedRequirement(
        topics=topics or ["AI Agent"],
        languages=_detect_terms(query, LANGUAGE_GROUPS),
        preferred_technologies=_detect_terms(query, TECHNOLOGY_GROUPS),
        required_capabilities=_detect_terms(query, CAPABILITY_GROUPS),
        difficulty=difficulty,
        goal=goal,
        excluded_features=_detect_exclusions(query),
    )


def build_search_plan(requirement: ParsedRequirement, *, now: datetime | None = None) -> SearchPlan:
    """根据结构化条件生成 3 到 5 条互补的 GitHub 查询。"""
    current_time = now or datetime.now(UTC)
    updated_after = current_time - timedelta(days=730)
    language = requirement.languages[0] if requirement.languages else None
    qualifiers = ["fork:false", "archived:false", f"pushed:>={updated_after.date().isoformat()}"]
    if language:
        qualifiers.insert(0, f"language:{language}")
    suffix = " ".join(qualifiers)

    primary_topic = requirement.topics[0]
    primary_tech = requirement.preferred_technologies[:2]
    capabilities = requirement.required_capabilities[:2]
    query_specs: list[tuple[str, str]] = [
        (
            " ".join([primary_topic, *primary_tech, suffix]),
            "优先匹配主题、技术栈和活跃度",
        ),
        (
            " ".join([primary_topic, *capabilities, "agent", suffix]),
            "补充搜索明确具备目标能力的工程",
        ),
        (
            " ".join([*requirement.topics[:2], "agent workflow", suffix]),
            "扩大到同类 Agent 工作流项目",
        ),
    ]
    if requirement.goal in {"resume_project", "secondary_development"}:
        query_specs.append(
            (
                " ".join([primary_topic, "api docker tests", suffix]),
                "寻找工程完整、适合改造和演示的项目",
            )
        )
    if len(requirement.preferred_technologies) > 2:
        query_specs.append(
            (
                " ".join([primary_topic, *requirement.preferred_technologies[2:4], suffix]),
                "覆盖次要偏好技术栈",
            )
        )

    unique_queries: list[SearchQuery] = []
    seen: set[str] = set()
    for query, purpose in query_specs:
        normalized_query = " ".join(query.split())
        if normalized_query.lower() in seen:
            continue
        seen.add(normalized_query.lower())
        unique_queries.append(SearchQuery(query=normalized_query, purpose=purpose))

    return SearchPlan(queries=unique_queries[:5], updated_after=updated_after)

