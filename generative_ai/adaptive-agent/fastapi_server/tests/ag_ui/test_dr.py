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

import asyncio
import uuid
from typing import Any, AsyncIterator, Callable, Coroutine, Iterator
from unittest.mock import patch

import pytest
from ag_ui.core import (
    BaseEvent,
    CustomEvent,
    Message,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallChunkEvent,
)
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)

from app.ag_ui.dr import DataRobotAGUIAgent
from app.config import Config


@pytest.fixture(scope="function")
def set_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[list[ChatCompletionChunk]], None]:
    """Fixture to mock OpenAI client responses"""
    mock_responses: list[ChatCompletionChunk] = []

    def mock_create(
        *args: Any, **kwargs: Any
    ) -> Coroutine[None, None, AsyncIterator[ChatCompletionChunk]]:
        async def foo() -> AsyncIterator[ChatCompletionChunk]:
            return generate(*mock_responses)

        return foo()

    monkeypatch.setattr(
        "openai.resources.chat.completions.AsyncCompletions.create", mock_create
    )

    def set(responses: list[ChatCompletionChunk]) -> None:
        mock_responses.clear()
        mock_responses.extend(responses)

    return set


@pytest.fixture(scope="function")
def set_completions_slow(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[list[ChatCompletionChunk]], None]:
    """Fixture to mock OpenAI client responses"""
    mock_responses: list[ChatCompletionChunk] = []

    def mock_create(
        *args: Any, **kwargs: Any
    ) -> Coroutine[None, None, AsyncIterator[ChatCompletionChunk]]:
        async def foo() -> AsyncIterator[ChatCompletionChunk]:
            return generate_slow(*mock_responses)

        return foo()

    monkeypatch.setattr(
        "openai.resources.chat.completions.AsyncCompletions.create", mock_create
    )

    def set(responses: list[ChatCompletionChunk]) -> None:
        mock_responses.clear()
        mock_responses.extend(responses)

    return set


@pytest.fixture(scope="function")
def error_completions(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[BaseException], None]:
    """Fixture to mock OpenAI client responses"""
    exception: list[BaseException] = []

    def mock_create(
        *args: Any, **kwargs: Any
    ) -> Coroutine[None, None, AsyncIterator[ChatCompletionChunk]]:
        async def foo() -> AsyncIterator[ChatCompletionChunk]:
            raise exception[0]

        return foo()

    monkeypatch.setattr(
        "openai.resources.chat.completions.AsyncCompletions.create", mock_create
    )

    def set(e: BaseException) -> None:
        exception.append(e)

    return set


@pytest.fixture
def name() -> Iterator[str]:
    yield "Test Agent"


@pytest.fixture
def model() -> Iterator[str]:
    yield "datarobot/openai/gpt-5-mini"


@pytest.fixture
def url() -> Iterator[str]:
    yield "https://localhost:8842"


@pytest.fixture
def dr_agui_agent(name: str, config: Config) -> Iterator[DataRobotAGUIAgent]:
    yield DataRobotAGUIAgent(name, config)


@pytest.fixture
def dr_agui_agent_heartbeat(name: str, config: Config) -> Iterator[DataRobotAGUIAgent]:
    yield DataRobotAGUIAgent(name, config, heartbeat_interval=0.1, check_interval=0.02)


def run_input(*messages: Message) -> RunAgentInput:
    return RunAgentInput(
        thread_id="thread",
        run_id="run",
        state=None,
        messages=list(messages),
        tools=[],
        context=[],
        forwarded_props=None,
    )


async def generate(*args: Any) -> AsyncIterator[Any]:
    for a in args:
        yield a


async def generate_slow(*args: Any) -> AsyncIterator[Any]:
    for a in args:
        await asyncio.sleep(0.1)
        yield a


async def run(agent: DataRobotAGUIAgent, *messages: Message) -> list[BaseEvent]:
    result = []
    async for event in agent.run(run_input(*messages)):
        result.append(event)
    return result


def chat_completions(
    *args: tuple[str, list[ChoiceDeltaToolCall]],
) -> list[ChatCompletionChunk]:
    return [
        ChatCompletionChunk(
            id="",
            model="",
            created=0,
            object="chat.completion.chunk",
            choices=[
                Choice(
                    finish_reason=None,
                    index=0,
                    delta=ChoiceDelta(content=content, tool_calls=tools),
                )
            ],
        )
        for content, tools in args
    ]


async def test_run_empty_response(
    set_completions: Callable[[list[ChoiceDelta]], None],
    dr_agui_agent: DataRobotAGUIAgent,
) -> None:
    set_completions([])
    with patch("uuid.uuid4") as uuid4:
        stub_uuid = "8825aa49-97ce-4fdf-9807-2ad9b4158acc"
        uuid4.return_value = uuid.UUID(stub_uuid)
        result = await run(dr_agui_agent)
        assert result == [
            RunStartedEvent(thread_id="thread", run_id="run"),
            RunErrorEvent(
                message="No response received from the agent. Please check if agent supports streaming."
            ),
        ]


async def test_run_failed_response(
    error_completions: Callable[[BaseException], None],
    dr_agui_agent: DataRobotAGUIAgent,
) -> None:
    error_completions(RuntimeError("Error"))
    result = await run(dr_agui_agent)
    with patch("uuid.uuid4") as uuid4:
        stub_uuid = "8825aa49-97ce-4fdf-9807-2ad9b4158acc"
        uuid4.return_value = uuid.UUID(stub_uuid)
        result = await run(dr_agui_agent)
        assert result == [
            RunStartedEvent(thread_id="thread", run_id="run"),
            RunErrorEvent(message="Error"),
        ]


async def test_run_single_message(
    set_completions: Callable[[list[ChatCompletionChunk]], None],
    dr_agui_agent: DataRobotAGUIAgent,
) -> None:
    set_completions(chat_completions(("Hi", [])))
    with patch("uuid.uuid4") as uuid4:
        stub_uuid = "8825aa49-97ce-4fdf-9807-2ad9b4158acc"
        uuid4.return_value = uuid.UUID(stub_uuid)
        result = await run(dr_agui_agent)
        assert result == [
            RunStartedEvent(thread_id="thread", run_id="run"),
            TextMessageStartEvent(
                message_id=stub_uuid,
            ),
            TextMessageContentEvent(message_id=stub_uuid, delta="Hi"),
            TextMessageEndEvent(message_id=stub_uuid),
            RunFinishedEvent(thread_id="thread", run_id="run"),
        ]


async def test_run_complex(
    set_completions: Callable[[list[ChatCompletionChunk]], None],
    dr_agui_agent: DataRobotAGUIAgent,
) -> None:
    set_completions(
        chat_completions(
            (
                "Hi",
                [
                    ChoiceDeltaToolCall(
                        index=0,
                        id="c1",
                        function=ChoiceDeltaToolCallFunction(arguments="a1", name="n1"),
                    ),
                    ChoiceDeltaToolCall(
                        index=0,
                        id="c2",
                    ),
                ],
            ),
            ("Bye", []),
        )
    )
    with patch("uuid.uuid4") as uuid4:
        uuid4.return_value = uuid.UUID("8825aa49-97ce-4fdf-9807-2ad9b4158acc")
        result = await run(dr_agui_agent)
        assert result == [
            RunStartedEvent(thread_id="thread", run_id="run"),
            TextMessageStartEvent(message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc"),
            TextMessageContentEvent(
                message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc", delta="Hi"
            ),
            ToolCallChunkEvent(
                parent_message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc",
                tool_call_id="c1",
                delta="a1",
                tool_call_name="n1",
            ),
            ToolCallChunkEvent(
                parent_message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc",
                tool_call_id="c2",
                delta=None,
                tool_call_name=None,
            ),
            TextMessageContentEvent(
                message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc", delta="Bye"
            ),
            TextMessageEndEvent(message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc"),
            RunFinishedEvent(thread_id="thread", run_id="run"),
        ]


async def test_run_complex_slow_stream(
    set_completions_slow: Callable[[list[ChatCompletionChunk]], None],
    dr_agui_agent_heartbeat: DataRobotAGUIAgent,
) -> None:
    set_completions_slow(
        chat_completions(
            (
                "Hi",
                [
                    ChoiceDeltaToolCall(
                        index=0,
                        id="c1",
                        function=ChoiceDeltaToolCallFunction(arguments="a1", name="n1"),
                    ),
                    ChoiceDeltaToolCall(
                        index=0,
                        id="c2",
                    ),
                ],
            ),
            ("Bye", []),
        )
    )
    with patch("uuid.uuid4") as uuid4:
        uuid4.return_value = uuid.UUID("8825aa49-97ce-4fdf-9807-2ad9b4158acc")
        result = await run(dr_agui_agent_heartbeat)
        assert result == [
            RunStartedEvent(thread_id="thread", run_id="run"),
            TextMessageStartEvent(message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc"),
            TextMessageContentEvent(
                message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc", delta="Hi"
            ),
            ToolCallChunkEvent(
                parent_message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc",
                tool_call_id="c1",
                delta="a1",
                tool_call_name="n1",
            ),
            ToolCallChunkEvent(
                parent_message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc",
                tool_call_id="c2",
                delta=None,
                tool_call_name=None,
            ),
            CustomEvent(
                name="Heartbeat", value={"thread_id": "thread", "run_id": "run"}
            ),
            TextMessageContentEvent(
                message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc", delta="Bye"
            ),
            TextMessageEndEvent(message_id="8825aa49-97ce-4fdf-9807-2ad9b4158acc"),
            RunFinishedEvent(thread_id="thread", run_id="run"),
        ]
