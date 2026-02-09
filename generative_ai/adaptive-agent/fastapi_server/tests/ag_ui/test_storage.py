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

from typing import AsyncGenerator, NamedTuple

import pytest
from ag_ui.core import (
    BaseEvent,
    Message,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    StepFinishedEvent,
    StepStartedEvent,
    TextMessageChunkEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ThinkingEndEvent,
    ThinkingStartEvent,
    ThinkingTextMessageContentEvent,
    ThinkingTextMessageEndEvent,
    ThinkingTextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallChunkEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
    UserMessage,
)
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.ag_ui.base import AGUIAgent
from app.ag_ui.storage import AGUIAgentWithStorage
from app.chats import ChatRepository
from app.db import DBCtx
from app.messages import MessageRepository, Role
from app.users.user import User, UserCreate, UserRepository


@pytest.fixture(scope="function")
async def in_memory_sqlite() -> DBCtx:
    # Technically makes these integration tests, but they should complete fast enough.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    ctx = DBCtx(engine)

    async with engine.connect() as async_conn:
        await async_conn.run_sync(SQLModel.metadata.create_all)

    return ctx


@pytest.fixture(scope="function")
def user_repo(in_memory_sqlite: DBCtx) -> UserRepository:
    return UserRepository(in_memory_sqlite)


@pytest.fixture(scope="function")
def chat_repo(in_memory_sqlite: DBCtx) -> ChatRepository:
    return ChatRepository(in_memory_sqlite)


@pytest.fixture(scope="function")
def message_repo(in_memory_sqlite: DBCtx) -> MessageRepository:
    return MessageRepository(in_memory_sqlite)


@pytest.fixture(scope="function")
async def user(user_repo: UserRepository) -> User:
    return await user_repo.create_user(
        UserCreate(first_name=None, last_name=None, email="example@dev")
    )


class StubAgent(AGUIAgent):
    def __init__(self, name: str):
        self._events: list[BaseEvent] = []
        super().__init__(name)

    def set_events(self, *events: BaseEvent) -> None:
        self._events = list(events)

    async def run(self, input: RunAgentInput) -> AsyncGenerator[BaseEvent, None]:
        for e in self._events:
            yield e


@pytest.fixture(scope="function")
def stub_agent() -> StubAgent:
    return StubAgent("stub-agent")


@pytest.fixture(scope="function")
async def storage_agent(
    user: User,
    chat_repo: ChatRepository,
    message_repo: MessageRepository,
    stub_agent: StubAgent,
) -> AGUIAgentWithStorage:
    return AGUIAgentWithStorage(
        name="storage-agent",
        user_id=user.uuid,
        chat_repo=chat_repo,
        message_repo=message_repo,
        inner=stub_agent,
    )


async def run(agent: AGUIAgent, thread_id: str, *messages: Message) -> list[BaseEvent]:
    events = []
    async for e in agent.run(
        RunAgentInput(
            thread_id=thread_id,
            run_id="r",
            state=None,
            messages=list(messages),
            tools=[],
            context=[],
            forwarded_props=None,
        )
    ):
        events.append(e)
    return events


async def test_no_response_chat_message_created(
    storage_agent: AGUIAgentWithStorage,
    stub_agent: StubAgent,
    chat_repo: ChatRepository,
    message_repo: MessageRepository,
) -> None:
    stub_agent.set_events()
    response = await run(
        storage_agent, "t1", UserMessage(id="m1", content="Hi", name="u1")
    )

    assert response == []

    chat = await chat_repo.get_chat_by_thread_id(
        user_uuid=storage_agent._user_id, thread_id="t1"
    )

    assert chat is not None

    message = await message_repo.get_message_by_agui_id(chat_id=chat.uuid, agui_id="m1")

    assert message is not None
    assert message.content == "Hi"
    assert message.name == "u1"
    assert message.role == "user"
    assert not message.reasonings
    assert not message.tool_calls

    await run(storage_agent, "t1", UserMessage(id="m1", content="Hi", name="u1"))

    chats = await chat_repo.get_all_chats(None)

    assert len(chats) == 1

    messages = await message_repo.get_chat_messages(chat.uuid)

    assert len(messages) == 1


async def test_chat_name_from_empty_string_content(
    storage_agent: AGUIAgentWithStorage,
    stub_agent: StubAgent,
    chat_repo: ChatRepository,
) -> None:
    stub_agent.set_events()
    await run(
        storage_agent,
        "t-chat-name",
        UserMessage(id="m1", content=" ", name="u1"),
    )

    chat = await chat_repo.get_chat_by_thread_id(
        user_uuid=storage_agent._user_id, thread_id="t-chat-name"
    )
    assert chat is not None
    assert chat.name == "New Chat"


class TC(NamedTuple):
    agui_id: str
    name: str
    argument: str
    content: str
    in_progress: bool = False
    error: str | None = None


class R(NamedTuple):
    name: str
    content: str
    in_progress: bool = False
    error: str | None = None


class M(NamedTuple):
    agui_id: str
    name: str
    content: str
    role: Role = Role.ASSISTANT
    step: str | None = None
    tool_calls: list[TC] = []
    reasonings: list[R] = []
    in_progress: bool = False
    error: str | None = None


class C(NamedTuple):
    thread_id: str
    messages: list[M]


class Run(NamedTuple):
    thread_id: str
    messages: list[Message]
    events: list[BaseEvent]


A = Role.ASSISTANT
U = Role.USER


@pytest.mark.parametrize(
    "input,expected",
    [
        # Single run with complete text message
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        TextMessageEndEvent(message_id="m2"),
                        RunFinishedEvent(thread_id="t1", run_id="r1"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2."),
                    ],
                )
            ],
        ),
        # Single run without finishing
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        TextMessageEndEvent(message_id="m2"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2."),
                    ],
                )
            ],
        ),
        # Single run without finishing
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2.", in_progress=True),
                    ],
                )
            ],
        ),
        # Single run with erroring before closing
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        RunErrorEvent(message="Failed"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2.", error="Failed"),
                    ],
                )
            ],
        ),
        # Single run with erroring after closing
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        TextMessageEndEvent(message_id="m2"),
                        RunErrorEvent(message="Failed"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2."),
                    ],
                )
            ],
        ),
        # Multi run with misbehaving text messages (unclosed).
        (
            [
                # No start.
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        RunErrorEvent(message="Failed"),
                    ],
                ),
                # Not finished
                Run(
                    "t2",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m3", delta="new"),
                    ],
                ),
                # Swaps back.
                Run(
                    "t3",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m3", delta="new"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                    ],
                ),
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2.", error="Failed"),
                    ],
                ),
                C(
                    "t2",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\n"),
                        M("m3", "storage-agent", "new", in_progress=True),
                    ],
                ),
                C(
                    "t3",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "part 1.\npart 2."),
                        M("m3", "storage-agent", "new"),
                    ],
                ),
            ],
        ),
        # Single run with steps
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        StepStartedEvent(step_name="s1"),
                        TextMessageChunkEvent(message_id="m2", delta="M2"),
                        TextMessageChunkEvent(message_id="m3", delta="M3"),
                        StepFinishedEvent(step_name="s1"),
                        TextMessageChunkEvent(message_id="m4", delta="M4"),
                        StepStartedEvent(step_name="s2"),
                        TextMessageChunkEvent(message_id="m5", delta="M5"),
                        StepFinishedEvent(step_name="s2"),
                        TextMessageChunkEvent(message_id="m6", delta="M6"),
                        RunFinishedEvent(thread_id="t1", run_id="r1"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M("m2", "storage-agent", "M2", step="s1"),
                        M("m3", "storage-agent", "M3", step="s1"),
                        M("m4", "storage-agent", "M4"),
                        M("m5", "storage-agent", "M5", step="s2"),
                        M("m6", "storage-agent", "M6"),
                    ],
                )
            ],
        ),
        # Successfull reasoning and tool calls
        (
            [
                Run(
                    "t1",
                    [UserMessage(id="m1", content="Hi", name="u1")],
                    [
                        RunStartedEvent(thread_id="t1", run_id="r1"),
                        TextMessageStartEvent(message_id="m2"),
                        TextMessageContentEvent(message_id="m2", delta="part 1.\n"),
                        TextMessageContentEvent(message_id="m2", delta="part 2."),
                        TextMessageEndEvent(message_id="m2"),
                        ToolCallStartEvent(
                            parent_message_id="m2",
                            tool_call_id="tc1",
                            tool_call_name="t1",
                        ),
                        ToolCallArgsEvent(tool_call_id="tc1", delta="a,"),
                        ToolCallArgsEvent(tool_call_id="tc1", delta="b"),
                        ToolCallEndEvent(tool_call_id="tc1"),
                        ToolCallResultEvent(
                            tool_call_id="tc1", content="TC1", message_id="tcm1"
                        ),
                        ThinkingStartEvent(title="Thinking"),
                        ThinkingTextMessageStartEvent(),
                        ThinkingTextMessageContentEvent(delta="t1\n"),
                        ThinkingTextMessageContentEvent(delta="t2"),
                        ThinkingTextMessageEndEvent(),
                        ThinkingTextMessageStartEvent(),
                        ThinkingTextMessageContentEvent(delta="t3"),
                        ThinkingTextMessageEndEvent(),
                        ThinkingEndEvent(),
                        ToolCallChunkEvent(
                            parent_message_id="m2",
                            tool_call_id="tc2",
                            tool_call_name="t2",
                            delta="x,y",
                        ),
                        ToolCallResultEvent(
                            tool_call_id="tc2", content="TC2", message_id="tcm1"
                        ),
                        RunFinishedEvent(thread_id="t1", run_id="r1"),
                    ],
                )
            ],
            [
                C(
                    "t1",
                    [
                        M("m1", "u1", "Hi", U),
                        M(
                            "m2",
                            "storage-agent",
                            "part 1.\npart 2.",
                            tool_calls=[
                                TC("tc1", "t1", "a,b", "TC1"),
                                TC("tc2", "t2", "x,y", "TC2"),
                            ],
                            reasonings=[R("Thinking", "t1\nt2"), R("Thinking", "t3")],
                        ),
                    ],
                )
            ],
        ),
    ],
)
async def test_parameterized(
    storage_agent: AGUIAgentWithStorage,
    stub_agent: StubAgent,
    chat_repo: ChatRepository,
    message_repo: MessageRepository,
    user: User,
    input: list[Run],
    expected: list[C],
) -> None:
    for thread_id, messages, events in input:
        stub_agent.set_events(*events)
        response = await run(storage_agent, thread_id, *messages)
        assert response == events, "Expected response to pass through all events."

    for expected_chat in expected:
        chat = await chat_repo.get_chat_by_thread_id(user.uuid, expected_chat.thread_id)
        assert chat is not None, (
            f"Expected thread with ID {expected_chat.thread_id} to be created."
        )
        for expected_message in expected_chat.messages:
            message = await message_repo.get_message_by_agui_id(
                chat.uuid, expected_message.agui_id
            )
            assert message is not None, (
                f"Expected message {expected_message.agui_id} to exist in thread {expected_chat.thread_id}"
            )
            assert message.name == expected_message.name, (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}. {message.name} == {expected_message.name}"
            )
            assert message.role == expected_message.role, (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}. {message.role} == {expected_message.role}"
            )
            assert message.content == expected_message.content, (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}. {repr(message.content)} == {repr(expected_message.content)}"
            )
            assert message.step == expected_message.step, (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}: '{message.step}' == '{expected_message.step}'"
            )

            assert len(message.reasonings) == len(expected_message.reasonings), (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}"
            )
            assert len(message.tool_calls) == len(expected_message.tool_calls), (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}"
            )

            actual_tool_calls = {
                TC(
                    agui_id=tc.tool_call_id or "MISSING",
                    name=tc.name,
                    content=tc.content,
                    argument=tc.arguments,
                    in_progress=tc.in_progress,
                    error=tc.error,
                )
                for tc in message.tool_calls
            }

            assert actual_tool_calls == set(expected_message.tool_calls), (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}. {actual_tool_calls}=={set(expected_message.tool_calls)}"
            )

            actual_reasonings = {
                R(r.name, r.content, r.in_progress, r.error) for r in message.reasonings
            }

            assert actual_reasonings == set(expected_message.reasonings), (
                f"Context: {expected_chat.thread_id}-{expected_message.agui_id}. {actual_reasonings}=={set(expected_message.reasonings)}"
            )
