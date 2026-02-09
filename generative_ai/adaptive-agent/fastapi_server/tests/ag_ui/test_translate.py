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

import uuid
from datetime import datetime

from ag_ui.core import FunctionCall, ToolCall

from app.ag_ui.translate import ExtendedBaseMessage, translate_messages
from app.messages import Message, MessageReasoning, MessageToolCall, Role


def test_translate_complex() -> None:
    uuids = [uuid.uuid4() for _ in range(10)]
    input = [
        Message(
            uuid=uuids[1],
            agui_id="m1",
            role=Role.ASSISTANT.value,
            content="Machine message",
            name="gpt",
            in_progress=True,
            error="message_error",
            created_at=datetime(2000, 1, 1),
            tool_calls=[
                MessageToolCall(
                    uuid=uuids[2],
                    message_uuid=uuids[1],
                    name="tool1",
                    content="output1",
                    arguments="args1",
                    in_progress=False,
                    error="Failed",
                    created_at=datetime(1980, 1, 1),
                ),
                MessageToolCall(
                    uuid=uuids[3],
                    agui_id="t2",
                    tool_call_id="t2",
                    message_uuid=uuids[1],
                    name="tool2",
                    content="output2",
                    arguments="args2",
                    in_progress=True,
                    created_at=datetime(1970, 1, 1),
                ),
            ],
            reasonings=[
                MessageReasoning(
                    uuid=uuids[5],
                    message_uuid=uuids[1],
                    agui_id="thought2",
                    in_progress=True,
                    created_at=datetime(1960, 1, 1),
                ),
                MessageReasoning(
                    uuid=uuids[4],
                    message_uuid=uuids[1],
                    name="Thinking",
                    content="Thoughts",
                    created_at=datetime(1950, 1, 1),
                    in_progress=False,
                ),
            ],
        ),
        Message(
            uuid=uuids[0],
            role=Role.USER.value,
            content="User message.",
            name="user1",
            in_progress=False,
            error=None,
            created_at=datetime(1940, 1, 1),
        ),
    ]
    expected = [
        ExtendedBaseMessage(
            id=str(uuids[0]),
            role="user",
            content="User message.",
            name="user1",
            in_progress=False,
            error=None,
        ),
        ExtendedBaseMessage(
            id="m1",
            role="assistant",
            content="Machine message",
            name="gpt",
            tool_calls=[
                ToolCall(
                    id="t2", function=FunctionCall(name="tool2", arguments="args2")
                ),
                ToolCall(
                    id=str(uuids[2]),
                    function=FunctionCall(name="tool1", arguments="args1"),
                ),
            ],
            in_progress=True,
            error="message_error",
        ),
        ExtendedBaseMessage(
            id="t2",
            role="tool",
            content="output2",
            name="tool2",
            in_progress=True,
            error=None,
        ),
        ExtendedBaseMessage(
            id=str(uuids[2]),
            role="tool",
            content="output1",
            name="tool1",
            in_progress=False,
            error="Failed",
        ),
        ExtendedBaseMessage(
            id=str(uuids[4]),
            role="reasoning",
            content="Thoughts",
            name="Thinking",
            in_progress=False,
            error=None,
        ),
        ExtendedBaseMessage(
            id="thought2",
            role="reasoning",
            content="",
            name="",
            in_progress=True,
            error=None,
        ),
    ]

    output = list(translate_messages(input))

    assert len(output) == len(expected)

    for i, (o, e) in enumerate(zip(output, expected)):
        assert o == e, f"Input/output differed at place {i}, {o} == {e}"
