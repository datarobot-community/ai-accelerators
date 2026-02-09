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

from typing import Iterable

from ag_ui.core import AssistantMessage, BaseMessage, FunctionCall, ToolCall

from app.messages import Message, Role


class ExtendedBaseMessage(BaseMessage):
    """AG UI base message with added in progress and error fields."""

    in_progress: bool
    error: str | None
    tool_calls: list[ToolCall] | None = None


def translate_messages(messages: Iterable[Message]) -> Iterable[ExtendedBaseMessage]:
    """
    Iterates through internal messages and transforms them to public messages.
    Order is message, then tool call results, then reasonings.

    Args:
        messages (Iterable[Message]): Internal message.

    Returns:
        Iterable[BaseMessage]: AGUI Message
    """
    sorted_messages = sorted(messages, key=lambda m: m.created_at)
    for message in sorted_messages:
        sorted_tool_calls = sorted(message.tool_calls, key=lambda tc: tc.created_at)

        out: BaseMessage
        if message.role == Role.ASSISTANT.value:
            out = AssistantMessage(
                id=message.agui_id or str(message.uuid),
                role=message.role,
                content=message.content,
                name=message.name,
                tool_calls=[
                    ToolCall(
                        id=tc.agui_id or str(tc.uuid),
                        function=FunctionCall(name=tc.name, arguments=tc.arguments),
                    )
                    for tc in sorted_tool_calls
                ],
            )
        else:
            out = BaseMessage(
                id=message.agui_id or str(message.uuid),
                role=message.role,
                content=message.content,
                name=message.name,
            )
        yield ExtendedBaseMessage(
            **out.model_dump(), in_progress=message.in_progress, error=message.error
        )
        for tc in sorted_tool_calls:
            yield ExtendedBaseMessage(
                id=tc.tool_call_id or str(tc.uuid),
                role=Role.TOOL.value,
                name=tc.name,
                content=tc.content,
                in_progress=tc.in_progress,
                error=tc.error,
            )
        for reasoning in sorted(message.reasonings, key=lambda r: r.created_at):
            yield ExtendedBaseMessage(
                id=reasoning.agui_id or str(reasoning.uuid),
                role=Role.REASONING.value,
                name=reasoning.name,
                content=reasoning.content,
                in_progress=reasoning.in_progress,
                error=reasoning.error,
            )
