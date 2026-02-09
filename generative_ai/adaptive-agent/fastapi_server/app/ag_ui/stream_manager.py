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
import queue
from collections.abc import AsyncGenerator
from functools import partial
from typing import Callable, Dict, Generic, ParamSpec, final
from uuid import UUID

from ag_ui.core import BaseEvent, RunAgentInput

from app.ag_ui.base import AGUIAgent
from app.ag_ui.dr import DataRobotAGUIAgent
from app.ag_ui.storage import AGUIAgentWithStorage
from app.chats import ChatRepository
from app.config import Config
from app.messages import MessageRepository

P = ParamSpec("P")


class NoMoreEvents:
    pass


@final
class AGUIStreamManager(Generic[P]):
    """
    This is a wrapper around an AGUIAgent that ensures that the whole output stream of the agent is consumed.
    The intention is to use this in concert with `AGUIAgentWithStorage` to make sure that the whole response
    from the agent is persisted even if the user disconnects from the stream midway.
    """

    def __init__(self, agent_factory: Callable[P, AGUIAgent]):
        self._agent_factory = agent_factory

    async def run(
        self, input: RunAgentInput, *args: P.args, **kwargs: P.kwargs
    ) -> AsyncGenerator[BaseEvent, None]:
        q: queue.Queue[BaseEvent | NoMoreEvents] = queue.Queue()

        async def populate_queue() -> None:
            agent = self._agent_factory(*args, **kwargs)
            async for event in agent.run(input):
                q.put(event)
            q.put(NoMoreEvents())

        async def iterate_queue() -> AsyncGenerator[BaseEvent, None]:
            while True:
                try:
                    e = q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.05)
                    continue
                if isinstance(e, NoMoreEvents):
                    break
                else:
                    yield e

        asyncio.create_task(populate_queue())

        return iterate_queue()


def _normalize_model_id(raw_model: str) -> str:
    """
    Add datarobot as a provider and handle any other provider string fixes for
    litellm
    """
    if raw_model.startswith("datarobot/"):
        return raw_model
    # fallback to datarobot provider
    return f"datarobot/{raw_model}"


def create_storage_dr_agent(
    name: str,
    chat_repo: ChatRepository,
    message_repo: MessageRepository,
    config: Config,
    user_id: UUID,
    headers: Dict[str, str],
) -> AGUIAgent:
    dr_agui = DataRobotAGUIAgent(name, config, headers)

    storage = AGUIAgentWithStorage(
        name=name,
        user_id=user_id,
        chat_repo=chat_repo,
        message_repo=message_repo,
        inner=dr_agui,
        minimal_chunk_to_persist=config.minimal_chunks_to_persist,
    )

    return storage


def create_stream_manager(
    name: str,
    chat_repo: ChatRepository,
    message_repo: MessageRepository,
    config: Config,
) -> AGUIStreamManager[UUID, Dict[str, str]]:
    factory = partial(create_storage_dr_agent, name, chat_repo, message_repo, config)
    return AGUIStreamManager(factory)
