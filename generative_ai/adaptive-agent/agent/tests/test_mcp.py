# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for MCP LangGraph integration - verifying agents have MCP tools configured.
"""

import asyncio
import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from langchain_core.messages import AIMessage

from agent import MyAgent


def create_mock_mcp_tool(name: str):
    """Create a mock MCP tool compatible with LangGraph agents."""

    async def mock_tool_func(ctx: Any, **kwargs: Any) -> str:
        return f"Result from {name}"

    mock_tool_func.__name__ = name
    mock_tool_func.__doc__ = f"Mock MCP tool {name}"
    return mock_tool_func


def _create_mock_astream():
    async def mock_astream(*args: Any, **kwargs: Any):
        yield (
            "planner_node",
            "updates",
            {
                "planner_node": {
                    "messages": [AIMessage(content="Test response")],
                    "usage": {
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                    },
                }
            },
        )

    return mock_astream


class _AsyncMCPContext:
    def __init__(self, tools_ref: dict[str, list[Any]]):
        self._tools_ref = tools_ref

    async def __aenter__(self) -> list[Any]:
        return self._tools_ref["value"]

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.fixture(autouse=True)
def langgraph_common_mocks():
    """
    Autouse fixture that centralizes LangGraph agent mocking:
    - Patches MCP context to return configurable tool lists
    - Patches workflow property to avoid executing a real LangGraph graph
    """
    default_tools = [
        create_mock_mcp_tool("fixture_mcp_tool_1"),
        create_mock_mcp_tool("fixture_mcp_tool_2"),
    ]
    tools_ref = {"value": default_tools}
    mock_execution_graph = MagicMock()
    mock_execution_graph.astream.side_effect = _create_mock_astream()

    with (
        patch(
            "datarobot_genai.langgraph.agent.mcp_tools_context",
            autospec=True,
        ) as mock_mcp_context,
        patch.object(
            MyAgent,
            "workflow",
            new_callable=PropertyMock,
        ) as mock_workflow_prop,
    ):
        mock_workflow = MagicMock()
        mock_workflow.compile.return_value = mock_execution_graph
        mock_workflow_prop.return_value = mock_workflow

        mock_mcp_context.side_effect = lambda *a, **k: _AsyncMCPContext(tools_ref)

        def set_mcp_tools(tools: list[Any]):
            tools_ref["value"] = tools

        def set_workflow_execution(stream_side_effect=_create_mock_astream()):
            mock_execution_graph.astream.side_effect = stream_side_effect

        yield SimpleNamespace(
            default_tools=default_tools,
            set_mcp_tools=set_mcp_tools,
            set_workflow=set_workflow_execution,
            mcp_context=mock_mcp_context,
        )


class TestMyAgentLangGraphMCPIntegration:
    """Test MCP tool integration for LangGraph agents."""

    def test_agent_loads_mcp_tools_from_external_url_in_invoke(
        self, langgraph_common_mocks
    ):
        mock_tools = langgraph_common_mocks.default_tools
        mock_context = langgraph_common_mocks.mcp_context

        test_url = "https://mcp-server.example.com/mcp"
        with patch.dict(os.environ, {"EXTERNAL_MCP_URL": test_url}, clear=True):
            agent = MyAgent(api_key="test_key", api_base="test_base", verbose=True)

            completion_params = {
                "messages": [{"role": "user", "content": "test prompt"}]
            }

            try:
                asyncio.run(agent.invoke(completion_params))
            except (StopIteration, AttributeError, TypeError, ValueError):
                pass

            mock_context.assert_called_once()
            assert mock_context.call_args.kwargs.get("authorization_context") == {}
            assert agent.mcp_tools == mock_tools

    def test_agent_loads_mcp_tools_from_datarobot_deployment_in_invoke(
        self, langgraph_common_mocks
    ):
        mock_tool = create_mock_mcp_tool("test_mcp_tool")
        mock_tools = [mock_tool]
        langgraph_common_mocks.set_mcp_tools(mock_tools)
        mock_context = langgraph_common_mocks.mcp_context

        deployment_id = "abc123def456789012345678"
        api_base = "https://app.datarobot.com/api/v2"
        api_key = "test-api-key"

        with patch.dict(
            os.environ,
            {
                "MCP_DEPLOYMENT_ID": deployment_id,
                "DATAROBOT_ENDPOINT": api_base,
                "DATAROBOT_API_TOKEN": api_key,
            },
            clear=True,
        ):
            agent = MyAgent(api_key=api_key, api_base=api_base, verbose=True)

            completion_params = {
                "messages": [{"role": "user", "content": "test prompt"}]
            }

            try:
                asyncio.run(agent.invoke(completion_params))
            except (StopIteration, AttributeError, TypeError, ValueError):
                pass

            mock_context.assert_called_once()
            assert mock_context.call_args.kwargs.get("authorization_context") == {}
            assert agent.mcp_tools == mock_tools

    def test_agent_works_without_mcp_tools(self, langgraph_common_mocks):
        langgraph_common_mocks.set_mcp_tools([])
        mock_context = langgraph_common_mocks.mcp_context

        with patch.dict(os.environ, {}, clear=True):
            agent = MyAgent(api_key="test_key", api_base="test_base", verbose=True)

            completion_params = {
                "messages": [{"role": "user", "content": "test prompt"}]
            }

            try:
                asyncio.run(agent.invoke(completion_params))
            except (StopIteration, AttributeError, TypeError, ValueError):
                pass

            mock_context.assert_called_once()
            assert len(agent.mcp_tools) == 0

    def test_mcp_tools_property_accessed_by_all_agents(self, langgraph_common_mocks):
        mock_tool1 = create_mock_mcp_tool("tool1")
        mock_tool2 = create_mock_mcp_tool("tool2")
        mock_tools = [mock_tool1, mock_tool2]
        langgraph_common_mocks.set_mcp_tools(mock_tools)

        access_count = {"count": 0}
        original_prop = MyAgent.mcp_tools

        def counting_prop(self):
            access_count["count"] += 1
            return original_prop.__get__(self, MyAgent)

        test_url = "https://mcp-server.example.com/mcp"
        with (
            patch.dict(os.environ, {"EXTERNAL_MCP_URL": test_url}, clear=True),
            patch.object(MyAgent, "mcp_tools", property(counting_prop)),
        ):
            agent = MyAgent(api_key="test_key", api_base="test_base", verbose=True)
            agent.set_mcp_tools(mock_tools)

            _ = agent.agent_planner
            _ = agent.agent_writer

        assert agent._mcp_tools == mock_tools
        assert access_count["count"] >= 2, (
            f"Expected at least 2 accesses (one per agent), got {access_count['count']}"
        )

    @patch("datarobot_genai.langgraph.mcp.load_mcp_tools", new_callable=AsyncMock)
    def test_mcp_tool_execution_makes_request_to_server(
        self, mock_load_mcp_tools, langgraph_common_mocks
    ):
        async def executable_tool(
            ctx: Any, query: str = "test query", **kwargs: Any
        ) -> str:
            return f"MCP server response for: {query}"

        executable_tool.__name__ = "test_executable_tool"
        executable_tool.__doc__ = "Test executable MCP tool"

        mock_tools = [executable_tool]
        mock_load_mcp_tools.return_value = mock_tools
        langgraph_common_mocks.set_mcp_tools(mock_tools)
        mock_context = langgraph_common_mocks.mcp_context

        test_url = "https://mcp-server.example.com/mcp"
        with patch.dict(os.environ, {"EXTERNAL_MCP_URL": test_url}, clear=True):
            agent = MyAgent(api_key="test_key", api_base="test_base", verbose=True)

            completion_params = {
                "messages": [{"role": "user", "content": "test prompt"}]
            }

            try:
                asyncio.run(agent.invoke(completion_params))
            except (StopIteration, AttributeError, TypeError, ValueError):
                pass

            mock_context.assert_called_once()
            assert len(agent.mcp_tools) == 1

            tool = agent.mcp_tools[0]
            result = asyncio.run(tool(ctx=MagicMock(), query="test query"))
            assert result == "MCP server response for: test query"
            assert callable(tool)
