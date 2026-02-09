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

from typing import AsyncGenerator

import pytest
from ag_ui.core import BaseEvent, RunAgentInput, RunFinishedEvent, RunStartedEvent

from app.ag_ui.base import AGUIAgent
from app.ag_ui.stream_manager import AGUIStreamManager


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


@pytest.fixture()
def stream_manager(stub_agent: StubAgent) -> AGUIStreamManager[[]]:
    return AGUIStreamManager(lambda: stub_agent)


async def test_returns_output(
    stub_agent: StubAgent, stream_manager: AGUIStreamManager[[]]
) -> None:
    events = [
        RunStartedEvent(thread_id="abc", run_id="123"),
        RunFinishedEvent(thread_id="abc", run_id="123"),
    ]
    stub_agent.set_events(*events)

    actual = []
    async for event in await stream_manager.run(
        input=RunAgentInput(
            thread_id="abc",
            run_id="123",
            state=None,
            messages=[],
            tools=[],
            context=[],
            forwarded_props=None,
        )
    ):
        actual.append(event)

    assert actual == events
