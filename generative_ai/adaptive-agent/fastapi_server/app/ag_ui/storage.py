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

import json
import logging
from dataclasses import dataclass
from typing import AsyncGenerator, final
from uuid import UUID, uuid4

from ag_ui.core import (
    AssistantMessage,
    BaseEvent,
    BaseMessage,
    RunAgentInput,
    UserMessage,
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
)

from app.ag_ui.base import AGUIAgent
from app.ag_ui.error_codes import ErrorCodes
from app.chats import Chat, ChatCreate, ChatRepository
from app.messages import (
    Message,
    MessageCreate,
    MessageReasoning,
    MessageReasoningCreate,
    MessageReasoningUpdate,
    MessageRepository,
    MessageToolCall,
    MessageToolCallCreate,
    MessageToolCallUpdate,
    MessageUpdate,
    Role,
)

logger = logging.getLogger(__name__)


@dataclass
class StorageStateMachineState:
    active_step: str | None = None
    active_reasoning_title: str | None = None
    active_reasoning: MessageReasoning | None = None
    active_tool_call: MessageToolCall | None = None
    active_message: Message | None = None
    unpersisted_characters: int = 0


@final
class AGUIAgentWithStorage(AGUIAgent):
    """A wrapper for an agent that stores messages."""

    def __init__(
        self,
        name: str,
        user_id: UUID,
        inner: AGUIAgent,
        chat_repo: ChatRepository,
        message_repo: MessageRepository,
        minimal_chunk_to_persist: int = 0,
    ):
        """
        Initialize an agent.

        Args:
            name (str): The name of this agent.
            user_id (UUID): The ID of the user creating this message
            inner (AGUIAgent): The agent this wraps. Only requirement is that the agent uses UUIDs as its message id format.
            chat_repo (ChatRepository): The repository of chats
            message_repo (MessageRepository): The repository of messages.
            minimal_chunk_to_persist (int): How many new characters we need before persisting (for agents that stream very small chunks)
        """
        super().__init__(name)
        if isinstance(inner, AGUIAgentWithStorage):
            raise ValueError(
                "Cannot wrap an AGUIAgentWithStorage with a second storage layer."
            )
        self._user_id = user_id
        self._inner = inner
        self._chat_repo = chat_repo
        self._message_repo = message_repo
        self._minimal_chunk_to_persist = minimal_chunk_to_persist

    async def run(self, input: RunAgentInput) -> AsyncGenerator[BaseEvent, None]:
        """
        This persists any incoming new user messages, runs the inner agent, and persists any messages.

        Args:
            input (RunAgentInput): The input

        Returns:
            AsyncGenerator[BaseEvent, None]: The inner agents event
        """
        existing_chat: Chat

        logger.debug(
            "Fetching initial chat",
            extra={"thread_id": input.thread_id, "user": str(self._user_id)},
        )

        if maybe_chat := await self._chat_repo.get_chat_by_thread_id(
            self._user_id, input.thread_id
        ):
            existing_chat = maybe_chat
        else:
            logger.debug(
                "Creating initial chat",
                extra={"thread_id": input.thread_id, "user": str(self._user_id)},
            )

            if (
                input.messages
                and isinstance(input.messages[0].content, str)
                and len(input.messages[0].content.strip()) > 0
            ):
                chat_name = input.messages[0].content[:20].strip()
            else:
                chat_name = "New Chat"

            existing_chat = await self._chat_repo.create_chat(
                ChatCreate(
                    user_uuid=self._user_id, name=chat_name, thread_id=input.thread_id
                )
            )

        # Load existing conversation history from database
        existing_messages = list(await self._message_repo.get_chat_messages(existing_chat.uuid))
        
        for message in input.messages:
            existing_message = await self._message_repo.get_message_by_agui_id(
                existing_chat.uuid, message.id
            )
            if existing_message:
                if existing_chat.uuid != existing_message.chat_id:
                    yield RunErrorEvent(
                        message="Messages do not all belong to the same chat",
                        code=ErrorCodes.INVALID_INPUT.value,
                    )
                    return
            else:
                if message.role != "user":
                    yield RunErrorEvent(
                        message="The user cannot create new non-user messages.",
                        code=ErrorCodes.INVALID_INPUT.value,
                    )
                    return

                await self._message_repo.create_message(
                    MessageCreate(
                        chat_id=existing_chat.uuid,
                        role=Role.USER.value,
                        agui_id=message.id,
                        name=message.name or "",
                        content=message.content,
                        error=None,
                        in_progress=False,
                    )
                )

        state = StorageStateMachineState()

        # Build full message history for the agent
        # Combine existing DB messages with new input messages
        all_messages: list[BaseMessage] = []
        
        # Add existing messages from DB (excluding messages already in input)
        input_message_ids = {m.id for m in input.messages}
        for db_msg in existing_messages:
            # Skip messages that are already in the input
            if db_msg.agui_id and db_msg.agui_id in input_message_ids:
                continue
            # Only include user and assistant messages (skip tool calls, reasoning, etc.)
            if db_msg.role == Role.USER.value:
                all_messages.append(
                    UserMessage(
                        id=db_msg.agui_id or str(db_msg.uuid),
                        role="user",
                        content=db_msg.content or "",
                        name=db_msg.name or None,
                    )
                )
            elif db_msg.role == Role.ASSISTANT.value:
                all_messages.append(
                    AssistantMessage(
                        id=db_msg.agui_id or str(db_msg.uuid),
                        role="assistant",
                        content=db_msg.content or "",
                        name=db_msg.name or None,
                    )
                )
        
        # Add new input messages
        all_messages.extend(input.messages)
        
        # Create new input with full history
        input_with_history = RunAgentInput(
            thread_id=input.thread_id,
            run_id=input.run_id,
            messages=all_messages,
            tools=input.tools,
            context=input.context,
            state=input.state,
            forwarded_props=input.forwarded_props,
        )
        
        logger.info(
            f"[STORAGE] Sending {len(all_messages)} messages to agent (thread_id={input.thread_id}, existing={len(existing_messages)}, new={len(input.messages)})"
        )

        async for event in self._inner.run(input_with_history):
            if isinstance(event, RunStartedEvent):
                state = StorageStateMachineState()
            if isinstance(event, RunFinishedEvent):
                if state.active_message:
                    await self._message_repo.update_message(
                        state.active_message.uuid, MessageUpdate(in_progress=False)
                    )
                if state.active_reasoning:
                    await self._message_repo.update_message_reasoning(
                        state.active_reasoning.uuid,
                        MessageReasoningUpdate(in_progress=False),
                    )
                if state.active_tool_call:
                    await self._message_repo.update_message_tool_call(
                        state.active_tool_call.uuid,
                        MessageToolCallUpdate(in_progress=False),
                    )
            if isinstance(event, RunErrorEvent):
                if event.code:
                    error = f"[{event.code}] {event.message}"
                else:
                    error = event.message
                if state.active_message:
                    await self._message_repo.update_message(
                        state.active_message.uuid,
                        MessageUpdate(in_progress=False, error=error),
                    )
                if state.active_reasoning:
                    await self._message_repo.update_message_reasoning(
                        state.active_reasoning.uuid,
                        MessageReasoningUpdate(in_progress=False, error=error),
                    )
                if state.active_tool_call:
                    await self._message_repo.update_message_tool_call(
                        state.active_tool_call.uuid,
                        MessageToolCallUpdate(in_progress=False, error=error),
                    )

            if isinstance(event, StepStartedEvent):
                state.active_step = event.step_name
            if isinstance(event, StepFinishedEvent):
                state.active_step = None

            await self._handle_text_message_events(state, existing_chat, event)
            await self._handle_tool_call_events(state, existing_chat, event)
            await self._handle_reasoning_event(state, existing_chat, event)

            yield event

    async def _handle_reasoning_event(
        self, state: StorageStateMachineState, existing_chat: Chat, event: BaseEvent
    ) -> None:
        # TODO: This is a placeholder as actual AGUI Reasoning is in draft https://docs.ag-ui.com/drafts/reasoning.
        # Should mostly be as simple as swapping the (deprecated) `Thinking...` events for `Reasoning...` events
        # when that draft is adopted.
        if isinstance(event, ThinkingStartEvent):
            state.active_reasoning_title = event.title
        if isinstance(event, ThinkingEndEvent):
            state.active_reasoning_title = None
            if state.active_reasoning:
                await self._message_repo.update_message_reasoning(
                    state.active_reasoning.uuid,
                    MessageReasoningUpdate(in_progress=False),
                )
                state.active_reasoning = None
        if isinstance(event, ThinkingTextMessageStartEvent):
            await self._ensure_message_exists(state, existing_chat, None, None)
            assert state.active_message, "Message created"
            await self._message_repo.create_message_reasoning(
                MessageReasoningCreate(
                    role=Role.REASONING.value,
                    message_uuid=state.active_message.uuid,
                    name=state.active_reasoning_title or "",
                )
            )
        if isinstance(event, ThinkingTextMessageContentEvent):
            await self._ensure_message_exists(state, existing_chat, None, None)
            assert state.active_message, "Message created"
            if not state.active_reasoning:
                # We need to ensure that active message is loaded here so that `reasonings` is live.
                assert state.active_message.chat_id and state.active_message.agui_id
                state.active_message = await self._message_repo.get_message_by_agui_id(
                    state.active_message.chat_id, state.active_message.agui_id
                )
                assert state.active_message
                if latest_reasoning := next(
                    iter(
                        sorted(
                            filter(
                                lambda r: r.in_progress, state.active_message.reasonings
                            ),
                            key=lambda r: r.created_at,
                            reverse=True,
                        )
                    ),
                    None,
                ):
                    state.active_reasoning = latest_reasoning
                else:
                    state.active_reasoning = (
                        await self._message_repo.create_message_reasoning(
                            MessageReasoningCreate(
                                role=Role.REASONING.value,
                                message_uuid=state.active_message.uuid,
                                name=state.active_reasoning_title or "",
                            )
                        )
                    )
            assert state.active_reasoning
            new_content = state.active_reasoning.content
            if isinstance(event.delta, str):
                new_content += event.delta
            elif isinstance(event.delta, list):
                new_content += "\n" + json.dumps(event.delta)
            else:
                logger.warning(
                    "Received reasoning '%s' of unanticipated type.", event.delta
                )
            state.active_reasoning.content = new_content
            await self._message_repo.update_message_reasoning(
                state.active_reasoning.uuid, MessageReasoningUpdate(content=new_content)
            )
        if isinstance(event, ThinkingTextMessageEndEvent):
            await self._ensure_message_exists(state, existing_chat, None, None)
            assert state.active_message, "Message created"
            if not state.active_reasoning:
                if latest_reasoning := next(
                    iter(
                        sorted(
                            filter(
                                lambda r: r.in_progress, state.active_message.reasonings
                            ),
                            key=lambda r: r.created_at,
                            reverse=True,
                        )
                    ),
                    None,
                ):
                    state.active_reasoning = latest_reasoning
                else:
                    state.active_reasoning = (
                        await self._message_repo.create_message_reasoning(
                            MessageReasoningCreate(
                                role=Role.REASONING.value,
                                message_uuid=state.active_message.uuid,
                                name=state.active_reasoning or "",
                            )
                        )
                    )
            assert state.active_reasoning
            await self._message_repo.update_message_reasoning(
                state.active_reasoning.uuid, MessageReasoningUpdate(in_progress=False)
            )
            state.active_reasoning = None

    async def _handle_tool_call_events(
        self, state: StorageStateMachineState, existing_chat: Chat, event: BaseEvent
    ) -> None:
        if isinstance(event, ToolCallStartEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                event.parent_message_id,
                None,
            )
            await self._ensure_tool_call_exists(
                state, event.tool_call_id, event.tool_call_name
            )
        if isinstance(event, ToolCallArgsEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                None,
                None,
            )
            await self._ensure_tool_call_exists(state, event.tool_call_id, None)
            assert state.active_tool_call, "Tool Call Created"
            await self._message_repo.update_message_tool_call(
                state.active_tool_call.uuid,
                MessageToolCallUpdate(
                    arguments=state.active_tool_call.arguments + event.delta
                ),
            )
        if isinstance(event, ToolCallResultEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                None,
                None,
            )
            await self._ensure_tool_call_exists(state, event.tool_call_id, None)
            assert state.active_tool_call, "Tool Call Created"
            await self._message_repo.update_message_tool_call(
                state.active_tool_call.uuid,
                MessageToolCallUpdate(content=event.content),
            )
        if isinstance(event, ToolCallEndEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                None,
                None,
            )
            await self._ensure_tool_call_exists(state, event.tool_call_id, None)
            assert state.active_tool_call, "Tool Call Created"
            await self._message_repo.update_message_tool_call(
                state.active_tool_call.uuid, MessageToolCallUpdate(in_progress=False)
            )
        if isinstance(event, ToolCallChunkEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                event.parent_message_id or str(uuid4()),
                None,
            )
            await self._ensure_tool_call_exists(
                state,
                event.tool_call_id
                or (state.active_tool_call and state.active_tool_call.tool_call_id)
                or str(uuid4()),
                event.tool_call_name,
            )
            assert state.active_tool_call, "Tool Call Created"
            await self._message_repo.update_message_tool_call(
                state.active_tool_call.uuid,
                MessageToolCallUpdate(
                    in_progress=False,
                    arguments=state.active_tool_call.arguments + (event.delta or ""),
                ),
            )

    async def _handle_text_message_events(
        self,
        state: StorageStateMachineState,
        existing_chat: Chat,
        event: BaseEvent,
    ) -> None:
        if isinstance(event, TextMessageStartEvent):
            await self._ensure_message_exists(
                state, existing_chat, event.message_id, event.role
            )
        if isinstance(event, TextMessageContentEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                event.message_id,
                None,
            )
            assert state.active_message, "Active message created."
            state.active_message.content += event.delta
            state.unpersisted_characters += len(event.delta)
            if state.unpersisted_characters >= self._minimal_chunk_to_persist:
                await self._message_repo.update_message(
                    state.active_message.uuid,
                    MessageUpdate(content=state.active_message.content),
                )
                state.unpersisted_characters = 0
        if isinstance(event, TextMessageEndEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                event.message_id,
                None,
            )
            assert state.active_message, "Active message created."
            message_update = MessageUpdate(in_progress=False)
            if state.unpersisted_characters:
                message_update.content = state.active_message.content
                state.unpersisted_characters = 0
            await self._message_repo.update_message(
                state.active_message.uuid, message_update
            )
        if isinstance(event, TextMessageChunkEvent):
            await self._ensure_message_exists(
                state,
                existing_chat,
                event.message_id or str(uuid4()),
                None,
            )
            assert state.active_message, "Active message created."

            await self._message_repo.update_message(
                state.active_message.uuid,
                MessageUpdate(
                    content=state.active_message.content + (event.delta or ""),
                    in_progress=False,
                ),
            )

    async def _ensure_message_exists(
        self,
        state: StorageStateMachineState,
        existing_chat: Chat,
        agui_id: str | None,
        role: str | None,
    ) -> None:
        """
        Return the assistant message in the chat matching the AGUI message ID. Refreshes the message if it exists.

        Args:
            active_step (str | None): The current step (can be None).
            existing_chat (Chat): The current chat.
            active_message (Message | None): The known current active message.
            agui_id (str | None): The desired message (if not provided, any assistant message will do).
            role (str | None): The role of the user leaving this message. Defaults to ASSISTANT.

        Returns:
            Message: _description_
        """
        active_message = state.active_message
        # If we are starting a new message, close out prior message.
        if agui_id and active_message and active_message.agui_id != agui_id:
            message_update = MessageUpdate(in_progress=False)
            if state.unpersisted_characters:
                message_update.content = active_message.content
            await self._message_repo.update_message(active_message.uuid, message_update)
            active_message = None

        if not active_message:
            state.unpersisted_characters = 0
            active_role: str | None = active_message.role if active_message else None
            active_agui_id: str | None = (
                active_message.agui_id if active_message else None
            )

            if agui_id:
                if retrieved_message := await self._message_repo.get_message_by_agui_id(
                    existing_chat.uuid, agui_id
                ):
                    active_message = retrieved_message
                else:
                    active_message = await self._message_repo.create_message(
                        MessageCreate(
                            step=state.active_step,
                            chat_id=existing_chat.uuid,
                            agui_id=agui_id,
                            role=role or active_role or Role.ASSISTANT.value,
                            name=self.name,
                            content="",
                            error=None,
                            in_progress=True,
                        )
                    )
            else:
                last_message = (
                    await self._message_repo.get_last_messages([existing_chat.uuid])
                )[existing_chat.uuid]
                if last_message.role == (role or Role.ASSISTANT.value):
                    active_message = last_message
                else:
                    active_message = await self._message_repo.create_message(
                        MessageCreate(
                            step=state.active_step,
                            chat_id=existing_chat.uuid,
                            agui_id=agui_id or active_agui_id,
                            role=role or active_role or Role.ASSISTANT.value,
                            name=self.name,
                            content="",
                            error=None,
                            in_progress=True,
                        )
                    )

        state.active_message = active_message

    async def _ensure_tool_call_exists(
        self,
        state: StorageStateMachineState,
        tool_call_id: str,
        tool_call_name: str | None,
    ) -> None:
        if not state.active_message:
            raise RuntimeError(
                f"Creating {tool_call_id} with no corresponding active message"
            )

        if not (
            active_tool_call := await self._message_repo.get_tool_call_by_agui_id(
                state.active_message.uuid, tool_call_id
            )
        ):
            active_tool_call = await self._message_repo.create_message_tool_call(
                MessageToolCallCreate(
                    tool_call_id=tool_call_id,
                    agui_id=tool_call_id,
                    message_uuid=state.active_message.uuid,
                    role=Role.TOOL.value,
                    name=tool_call_name or "UNKNOWN",
                )
            )
        state.active_tool_call = active_tool_call
