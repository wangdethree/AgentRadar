"""智能搜索的 LangGraph 工作流与无依赖顺序执行器。"""

from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.agents.state import SearchSessionState
from app.models.search import SearchSession
from app.repositories.analysis_repository import AnalysisReportRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.search_session_repository import SearchSessionRepository
from app.services.filter_service import normalize_and_filter, screen_candidates
from app.services.requirement_service import build_search_plan, parse_requirement
from app.services.research_service import ResearchService
from app.services.scoring_service import build_recommendations
from app.tools.github.client import GitHubClient
from app.tools.github.errors import GitHubAPIError
from app.tools.github.search import search_repositories

NodeResult = tuple[dict[str, Any], str, list[str]]
NodeOperation = Callable[[SearchSessionState], Awaitable[NodeResult]]


class SearchWorkflow:
    """执行需求理解、搜索、过滤、初筛、目标选择和持久化。"""

    def __init__(self, session: Session, github_client: GitHubClient) -> None:
        self.session_store = SearchSessionRepository(session)
        self.github_client = github_client

    async def run(
        self,
        user_query: str,
        *,
        prefer_langgraph: bool = True,
    ) -> SearchSessionState:
        """创建会话并执行基础搜索；缺少 LangGraph 时使用同节点顺序执行。"""
        search_session = self.session_store.create(user_query)
        self.session_store.mark_running(search_session)
        initial_state: SearchSessionState = {
            "session_id": search_session.id,
            "user_query": user_query,
            "search_round": 0,
            "tool_call_count": 0,
            "llm_call_count": 0,
            "errors": [],
        }

        try:
            if prefer_langgraph:
                try:
                    graph = self.compile()
                except ModuleNotFoundError as error:
                    if error.name != "langgraph":
                        raise
                    return await self._run_sequential(initial_state, search_session)
                result = await graph.ainvoke(initial_state)
                return SearchSessionState(**result)
            return await self._run_sequential(initial_state, search_session)
        except Exception as error:
            self.session_store.mark_failed(search_session, error)
            raise

    def compile(self) -> Any:
        """构建与计划书节点一致的 LangGraph；导入延迟到运行时。"""
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(SearchSessionState)
        builder.add_node("parse_requirement", self.parse_requirement_node)
        builder.add_node("build_search_plan", self.build_search_plan_node)
        builder.add_node("search_github", self.search_github_node)
        builder.add_node("normalize_and_filter", self.normalize_and_filter_node)
        builder.add_node("screen_candidates", self.screen_candidates_node)
        builder.add_node("select_research_targets", self.select_research_targets_node)
        builder.add_node("research_repository", self.research_repository_node)
        builder.add_node("score_and_rank", self.score_and_rank_node)
        builder.add_node("generate_recommendations", self.generate_recommendations_node)
        builder.add_node("persist_session", self.persist_session_node)
        builder.add_edge(START, "parse_requirement")
        builder.add_edge("parse_requirement", "build_search_plan")
        builder.add_edge("build_search_plan", "search_github")
        builder.add_edge("search_github", "normalize_and_filter")
        builder.add_edge("normalize_and_filter", "screen_candidates")
        builder.add_edge("screen_candidates", "select_research_targets")
        builder.add_edge("select_research_targets", "research_repository")
        builder.add_edge("research_repository", "score_and_rank")
        builder.add_edge("score_and_rank", "generate_recommendations")
        builder.add_edge("generate_recommendations", "persist_session")
        builder.add_edge("persist_session", END)
        return builder.compile()

    async def _run_sequential(
        self,
        state: SearchSessionState,
        search_session: SearchSession,
    ) -> SearchSessionState:
        """使用同一组节点提供可测试的本地降级路径。"""
        node_sequence = (
            self.parse_requirement_node,
            self.build_search_plan_node,
            self.search_github_node,
            self.normalize_and_filter_node,
            self.screen_candidates_node,
            self.select_research_targets_node,
            self.research_repository_node,
            self.score_and_rank_node,
            self.generate_recommendations_node,
            self.persist_session_node,
        )
        for node in node_sequence:
            state.update(await node(state))
        if search_session.status != "completed":  # pragma: no cover - 防御性分支
            self.session_store.mark_completed(search_session)
        return state

    async def _execute_node(
        self,
        node_name: str,
        state: SearchSessionState,
        operation: NodeOperation,
        input_summary: str,
    ) -> dict[str, Any]:
        """执行节点并记录耗时、工具和安全摘要。"""
        started_at = perf_counter()
        search_session = self._require_session(state["session_id"])
        try:
            updates, output_summary, tools = await operation(state)
        except Exception as error:
            self.session_store.add_trace(
                search_session,
                node_name=node_name,
                input_summary=input_summary,
                output_summary=None,
                duration_ms=int((perf_counter() - started_at) * 1000),
                error_message=f"{type(error).__name__}: {str(error)[:500]}",
            )
            raise
        self.session_store.add_trace(
            search_session,
            node_name=node_name,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=int((perf_counter() - started_at) * 1000),
            tool_names=tools,
        )
        return updates

    async def parse_requirement_node(self, state: SearchSessionState) -> dict[str, Any]:
        """结构化用户需求。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            requirement = parse_requirement(state["user_query"])
            capability_count = len(requirement.required_capabilities)
            return (
                {"parsed_requirement": requirement},
                f"识别 {len(requirement.topics)} 个主题和 {capability_count} 项能力",
                [],
            )

        return await self._execute_node(
            "parse_requirement",
            state,
            operation,
            "解析用户自然语言需求",
        )

    async def build_search_plan_node(self, state: SearchSessionState) -> dict[str, Any]:
        """生成互补 GitHub 搜索语句。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            plan = build_search_plan(state["parsed_requirement"])
            return ({"search_plan": plan}, f"生成 {len(plan.queries)} 条搜索语句", [])

        return await self._execute_node(
            "build_search_plan",
            state,
            operation,
            "根据结构化条件生成搜索计划",
        )

    async def search_github_node(self, state: SearchSessionState) -> dict[str, Any]:
        """按计划执行多组 GitHub 搜索，单条失败不终止整轮。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            plan = state["search_plan"]
            discovered = []
            errors = list(state.get("errors", []))
            successful_calls = 0
            for search_query in plan.queries:
                try:
                    page = await search_repositories(
                        self.github_client,
                        search_query.query,
                        per_page=search_query.max_results,
                    )
                except GitHubAPIError as error:
                    errors.append({"query": search_query.query, "code": error.code})
                    continue
                successful_calls += 1
                discovered.extend(page.items)

            if successful_calls == 0:
                raise GitHubAPIError(
                    "全部 GitHub 搜索均失败",
                    code="github_all_searches_failed",
                    retryable=True,
                )
            return (
                {
                    "discovered_repositories": discovered,
                    "search_round": state.get("search_round", 0) + 1,
                    "tool_call_count": state.get("tool_call_count", 0) + len(plan.queries),
                    "errors": errors,
                },
                f"发现 {len(discovered)} 条候选记录，{len(errors)} 条查询失败",
                ["search_repositories"],
            )

        return await self._execute_node(
            "search_github",
            state,
            operation,
            f"执行 {len(state['search_plan'].queries)} 条 GitHub 查询",
        )

    async def normalize_and_filter_node(self, state: SearchSessionState) -> dict[str, Any]:
        """执行去重和硬规则过滤。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            plan = state["search_plan"]
            outcome = normalize_and_filter(
                state["discovered_repositories"],
                ignored_full_names=InteractionRepository(
                    self.session_store.session
                ).ignored_full_names(),
                updated_after=plan.updated_after,
                max_candidates=plan.max_candidates,
            )
            removed_total = sum(outcome.removed_counts.values())
            return (
                {"filtered_repositories": outcome.repositories},
                f"保留 {len(outcome.repositories)} 个候选，规则移除 {removed_total} 个",
                [],
            )

        return await self._execute_node(
            "normalize_and_filter",
            state,
            operation,
            f"处理 {len(state['discovered_repositories'])} 条候选记录",
        )

    async def screen_candidates_node(self, state: SearchSessionState) -> dict[str, Any]:
        """根据需求相关度进行低成本初筛。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            screened = screen_candidates(
                state["filtered_repositories"],
                state["parsed_requirement"],
            )
            deep_count = sum(item.research_level == "deep" for item in screened)
            return (
                {"screened_repositories": screened},
                f"初筛 {len(screened)} 个项目，其中 {deep_count} 个建议深度调查",
                [],
            )

        return await self._execute_node(
            "screen_candidates",
            state,
            operation,
            f"评估 {len(state['filtered_repositories'])} 个仓库",
        )

    async def select_research_targets_node(self, state: SearchSessionState) -> dict[str, Any]:
        """从非 skip 项目中选择最多五个研究目标。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            limit = state["search_plan"].max_research_targets
            targets = [
                item for item in state["screened_repositories"] if item.research_level != "skip"
            ][:limit]
            return (
                {"research_targets": targets},
                f"选择 {len(targets)} 个项目进入研究阶段",
                [],
            )

        return await self._execute_node(
            "select_research_targets",
            state,
            operation,
            "按相关度和调查等级选择目标",
        )

    async def persist_session_node(self, state: SearchSessionState) -> dict[str, Any]:
        """保存计划、初筛结果、研究目标和完成状态。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            search_session = self._require_session(state["session_id"])
            self.session_store.save_plan(
                search_session,
                state["parsed_requirement"],
                state["search_plan"],
            )
            self.session_store.replace_stage_results(
                search_session,
                stage="screened",
                items=state["screened_repositories"],
            )
            self.session_store.replace_stage_results(
                search_session,
                stage="research_target",
                items=state["research_targets"],
            )
            report_store = AnalysisReportRepository(self.session_store.session)
            for report in state["research_reports"]:
                report_store.save(report)
            self.session_store.replace_final_results(
                search_session,
                state["final_recommendations"],
            )
            self.session_store.mark_completed(search_session)
            return ({}, "搜索会话、结果和轨迹已保存", [])

        return await self._execute_node(
            "persist_session",
            state,
            operation,
            "持久化结构化搜索结果",
        )

    async def research_repository_node(self, state: SearchSessionState) -> dict[str, Any]:
        """按初筛等级调查仓库，单个项目失败时继续其余项目。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            service = ResearchService(self.github_client)
            reports = []
            errors = list(state.get("errors", []))
            for target in state["research_targets"]:
                try:
                    reports.append(
                        await service.research(
                            target.repository,
                            report_type="deep" if target.research_level == "deep" else "shallow",
                        )
                    )
                except Exception as error:  # 单仓库失败不能终止整轮搜索
                    errors.append(
                        {
                            "repository": target.repository.full_name,
                            "code": type(error).__name__,
                        }
                    )
            return (
                {
                    "research_reports": reports,
                    "tool_call_count": state.get("tool_call_count", 0)
                    + len(state["research_targets"]) * 5,
                    "errors": errors,
                },
                f"完成 {len(reports)} 个项目调查，累计 {len(errors)} 个非致命错误",
                [
                    "get_readme",
                    "get_repository_tree",
                    "get_file_content",
                    "get_releases",
                    "get_issues",
                ],
            )

        return await self._execute_node(
            "research_repository",
            state,
            operation,
            f"调查 {len(state['research_targets'])} 个候选项目",
        )

    async def score_and_rank_node(self, state: SearchSessionState) -> dict[str, Any]:
        """计算六维评分并按总分排序。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            recommendations = build_recommendations(
                state["research_targets"],
                state["research_reports"],
                state["parsed_requirement"],
            )
            return (
                {"scored_recommendations": recommendations},
                f"完成 {len(recommendations)} 个项目的六维评分",
                [],
            )

        return await self._execute_node(
            "score_and_rank",
            state,
            operation,
            "结合相关度、技术栈、Agent 能力、工程质量、活跃度与难度评分",
        )

    async def generate_recommendations_node(self, state: SearchSessionState) -> dict[str, Any]:
        """生成最多三个最终推荐卡。"""

        async def operation(_: SearchSessionState) -> NodeResult:
            recommendations = state["scored_recommendations"][:3]
            return (
                {"final_recommendations": recommendations},
                f"生成 {len(recommendations)} 个最终推荐",
                [],
            )

        return await self._execute_node(
            "generate_recommendations",
            state,
            operation,
            "生成包含证据、风险和阅读路径的推荐卡",
        )

    def _require_session(self, session_id: str) -> SearchSession:
        """读取会话；内部状态丢失时立即失败。"""
        search_session = self.session_store.get(session_id)
        if search_session is None:
            raise RuntimeError(f"搜索会话不存在：{session_id}")
        return search_session
