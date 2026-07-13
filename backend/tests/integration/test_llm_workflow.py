"""可选模型增强工作流集成测试。"""

import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.agents.graph import SearchWorkflow
from app.core.config import Settings
from app.models import Base, ExecutionTrace
from app.providers.llm import LLMClient
from app.tools.github.client import GitHubClient
from tests.integration.test_search_workflow import github_handler


def structured_response(content: dict[str, object]) -> httpx.Response:
    """为每次模型增强返回可验证的结构化结果。"""
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"total_tokens": 21},
        },
    )


def successful_llm_handler(request: httpx.Request) -> httpx.Response:
    """按 Prompt 类型返回需求解析或候选初筛结果。"""
    body = json.loads(request.content)
    prompt = body["messages"][1]["content"]
    if prompt.startswith("解析下面"):
        return structured_response(
            {
                "topics": ["LangGraph"],
                "languages": ["Python"],
                "preferred_technologies": ["FastAPI", "LangGraph"],
                "required_capabilities": ["tool calling", "state management"],
                "difficulty": "intermediate",
                "goal": "resume_project",
                "excluded_features": ["CrewAI"],
            }
        )
    return structured_response(
        {
            "decisions": [
                {
                    "full_name": "example/langgraph-fastapi-agent",
                    "relevance_score": 98,
                    "research_level": "deep",
                    "reasons": ["模型确认技术栈与目标能力均匹配"],
                },
                {
                    "full_name": "attacker/invented-repository",
                    "relevance_score": 100,
                    "research_level": "deep",
                    "reasons": ["该仓库不在真实候选中"],
                },
            ]
        }
    )


def build_settings() -> tuple[Settings, Settings]:
    """分别构造 GitHub 与模型测试配置。"""
    github_settings = Settings(
        _env_file=None,
        github_api_url="https://api.github.test",
        github_max_retries=0,
    )
    llm_settings = Settings(
        _env_file=None,
        llm_base_url="https://llm.test/v1",
        llm_model="test-model",
        llm_max_retries=0,
    )
    return github_settings, llm_settings


@pytest.mark.anyio
async def test_workflow_uses_llm_without_allowing_invented_candidates() -> None:
    """模型可增强解析和初筛，但不能把虚构仓库加入候选。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    github_settings, llm_settings = build_settings()

    with Session(engine) as session:
        async with (
            GitHubClient(
                github_settings,
                transport=httpx.MockTransport(github_handler),
            ) as github_client,
            LLMClient(
                llm_settings,
                transport=httpx.MockTransport(successful_llm_handler),
            ) as llm_client,
        ):
            state = await SearchWorkflow(session, github_client, llm_client).run(
                "找 Python LangGraph FastAPI 简历项目，不要 CrewAI",
                prefer_langgraph=False,
            )
            refined_state = await SearchWorkflow(session, github_client, llm_client).refine(
                state["session_id"],
                "继续优先工程完整、适合简历的项目",
            )
        traces = list(session.scalars(select(ExecutionTrace).order_by(ExecutionTrace.id)))
        refine_trace = next(item for item in traces if item.node_name == "refine_session")

    assert state["llm_call_count"] == 2
    assert state["parsed_requirement"].difficulty == "intermediate"
    assert state["screened_repositories"][0].relevance_score == 98
    assert [item.repository.full_name for item in state["screened_repositories"]] == [
        "example/langgraph-fastapi-agent"
    ]
    assert sum(item.token_usage or 0 for item in traces) == 84
    assert [item.node_name for item in traces if item.token_usage] == [
        "parse_requirement",
        "screen_candidates",
        "refine_session",
    ]
    assert refined_state["llm_call_count"] == 2
    assert refine_trace.token_usage == 42
    assert refine_trace.tool_names == ["llm:parse_requirement", "llm:screen_candidates"]


@pytest.mark.anyio
async def test_workflow_falls_back_to_rules_when_llm_is_unavailable() -> None:
    """模型服务失败只记录非致命错误，GitHub 搜索与推荐仍应完成。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    github_settings, llm_settings = build_settings()

    def unavailable_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    with Session(engine) as session:
        async with (
            GitHubClient(
                github_settings,
                transport=httpx.MockTransport(github_handler),
            ) as github_client,
            LLMClient(
                llm_settings,
                transport=httpx.MockTransport(unavailable_handler),
            ) as llm_client,
        ):
            state = await SearchWorkflow(session, github_client, llm_client).run(
                "寻找 Python LangGraph FastAPI 项目，包含工具调用和状态管理，适合简历",
                prefer_langgraph=False,
            )

    assert state["llm_call_count"] == 2
    assert len(state["errors"]) == 2
    assert {item["code"] for item in state["errors"]} == {"llm_http_error"}
    assert len(state["final_recommendations"]) == 1
