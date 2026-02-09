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
import uuid as uuidpkg
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence, cast

from sqlalchemy import Column, DateTime, ForeignKey, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from sqlmodel import Field, Index, Relationship, SQLModel, UniqueConstraint, select

from app.db import DBCtx

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """Message source role"""

    # CF. https://docs.ag-ui.com/concepts/messages

    DEVELOPER = "developer"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    USER = "user"
    TOOL = "tool"
    REASONING = "reasoning"


class AGUIMessageBase(SQLModel):
    agui_id: str | None = Field(default=None)
    role: str = Field(default=Role.USER)
    name: str = Field(default="")

    content: str = Field(default="")


class MessageBase(AGUIMessageBase):
    """Base model for messages (following AG-UI schema)."""

    step: str | None = Field(default=None)

    chat_id: uuidpkg.UUID | None = Field(
        default=None,
        sa_column=Column(
            "chat_id", ForeignKey("chat.uuid", ondelete="CASCADE"), index=True
        ),
    )

    in_progress: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )
    error: str | None = Field(default=None)

    __table_args__ = (
        UniqueConstraint("chat_id", "agui_id", name="uq_chat_id_agui_id"),
        Index("ix_chat_id_agui_id", "chat_id", "agui_id"),
    )

    def dump_json_compatible(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.model_dump_json()))


class MessageToolCallBase(AGUIMessageBase):
    """
    Base model for message tool
    """

    message_uuid: uuidpkg.UUID = Field(
        foreign_key="message.uuid", ondelete="CASCADE", index=True
    )
    tool_call_id: str | None = Field(default=None)
    role: str = Field(default=Role.TOOL.value)
    name: str = Field(default="")

    arguments: str = Field(default="")
    in_progress: bool = Field(default=True)
    error: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )

    __table_args__ = (
        UniqueConstraint("message_uuid", "agui_id", name="unq_message_uuid_agui_id"),
        Index("ix_message_uuid_agui_id", "message_uuid", "agui_id"),
    )


class MessageReasoningBase(AGUIMessageBase):
    """
    Base model for reasoning component of a message.
    """

    message_uuid: uuidpkg.UUID = Field(
        foreign_key="message.uuid", ondelete="CASCADE", index=True
    )
    role: str = Field(default=Role.REASONING.value)

    in_progress: bool = Field(default=True)
    error: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False, index=True),
    )


class MessageToolCall(MessageToolCallBase, table=True):
    """Schema for a tool call in a message."""

    __tablename__ = "message_tool_call"

    uuid: uuidpkg.UUID = Field(
        default_factory=uuidpkg.uuid4, primary_key=True, unique=True
    )
    message: "Message" = Relationship(back_populates="tool_calls")


class MessageReasoning(MessageReasoningBase, table=True):
    """Schema for reasoning components of a message."""

    __tablename__ = "message_reasoning"

    uuid: uuidpkg.UUID = Field(
        default_factory=uuidpkg.uuid4, primary_key=True, unique=True
    )
    message: "Message" = Relationship(back_populates="reasonings")


class Message(MessageBase, table=True):
    uuid: uuidpkg.UUID = Field(
        default_factory=uuidpkg.uuid4, primary_key=True, unique=True
    )
    tool_calls: list["MessageToolCall"] = Relationship(back_populates="message")
    reasonings: list["MessageReasoning"] = Relationship(back_populates="message")


class MessagePublic(MessageBase):
    """
    Schema for message with tools/reasoning, without recursive relationships (for safe serialization.)
    """

    uuid: uuidpkg.UUID = Field(default_factory=uuidpkg.uuid4)
    tool_calls: list[MessageToolCallBase] = Field(default_factory=list)
    reasonings: list[MessageReasoningBase] = Field(default_factory=list)


class MessageCreate(MessageBase):
    """
    Schema for creating a new message.
    """


class MessageUpdate(SQLModel):
    """
    Schema for updating an existing message. All fields optional.
    """

    content: str | None = Field(default="")
    error: str | None = Field(default=None)
    in_progress: bool | None = Field(default=False)


class MessageToolCallCreate(MessageToolCallBase):
    """
    Schema for creating a new tool call in a message
    """


class MessageToolCallUpdate(SQLModel):
    """
    Schema for updating an existing tool call in a message. All fields optional.
    """

    arguments: str | None = Field(default="")
    content: str | None = Field(default="")
    error: str | None = Field(default=None)
    in_progress: bool | None = Field(default=False)


class MessageReasoningCreate(MessageReasoningBase):
    """
    Schema for creating a new piece of message reasoning.
    """


class MessageReasoningUpdate(SQLModel):
    """
    Schema for updating an existing reasoning in a message. All fields optional.
    """

    content: str | None = Field(default="")
    error: str | None = Field(default=None)
    in_progress: bool | None = Field(default=False)


class MessageRepository:
    """
    Message repository class to handle message-related database operations.
    """

    def __init__(self, db: DBCtx):
        self._db = db

    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        Add a new message to the database with chat existence validation.
        This method ensures the chat exists before creating the message.
        """

        message = Message(**message_data.model_dump())

        async with self._db.session(writable=True) as session:
            session.add(message)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError(f"Chat with ID {message_data.chat_id} does not exist")
            await session.refresh(message)
            return message

    async def update_message(
        self,
        uuid: uuidpkg.UUID,
        update: "MessageUpdate",
    ) -> Message | None:
        """Update a message (must be owned by the user)."""
        logger.debug("Writing message")
        async with self._db.session(writable=True) as session:
            query = await session.exec(
                select(Message)
                .where(
                    Message.uuid == uuid,
                )
                .options(selectinload("*"))
            )
            message = query.first()
            if not message:
                return None

            for field, value in update.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(message, field, value)

            await session.commit()
            await session.refresh(message)

            return message

    async def create_message_tool_call(
        self, message_tool_call_data: MessageToolCallCreate
    ) -> MessageToolCall:
        """
        Create a tool call for a message.
        """
        message_tool_call = MessageToolCall(**message_tool_call_data.model_dump())
        async with self._db.session(writable=True) as session:
            session.add(message_tool_call)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError(
                    f"Message with ID {message_tool_call_data.message_uuid} does not exist"
                )
            await session.refresh(message_tool_call)
            return message_tool_call

    async def update_message_tool_call(
        self, uuid: uuidpkg.UUID, update: MessageToolCallUpdate
    ) -> MessageToolCall | None:
        """
        Updates a tool call in a message.
        """
        async with self._db.session(writable=True) as session:
            query = await session.exec(
                select(MessageToolCall)
                .where(
                    MessageToolCall.uuid == uuid,
                )
                .options(selectinload("*"))
            )
            tool_call = query.first()
            if not tool_call:
                return None

            for field, value in update.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(tool_call, field, value)

            await session.commit()
            await session.refresh(tool_call)
            return tool_call

    async def create_message_reasoning(
        self, message_tool_call_data: MessageReasoningCreate
    ) -> MessageReasoning:
        """
        Create a tool call for a message.
        """
        reasoning = MessageReasoning(**message_tool_call_data.model_dump())
        async with self._db.session(writable=True) as session:
            session.add(reasoning)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise ValueError(
                    f"Message with ID {message_tool_call_data.message_uuid} does not exist"
                )
            await session.refresh(reasoning)
            return reasoning

    async def update_message_reasoning(
        self, uuid: uuidpkg.UUID, update: MessageReasoningUpdate
    ) -> MessageReasoning | None:
        """
        Updates a tool call in a message.
        """
        async with self._db.session(writable=True) as session:
            query = await session.exec(
                select(MessageReasoning)
                .where(
                    MessageReasoning.uuid == uuid,
                )
                .options(selectinload("*"))
            )
            reasoning = query.first()
            if not reasoning:
                return None

            for field, value in update.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(reasoning, field, value)

            await session.commit()
            await session.refresh(reasoning)
            return reasoning

    async def get_message(self, uuid: uuidpkg.UUID) -> Message | None:
        """
        Retrieve a message by their ID.
        """
        async with self._db.session() as sess:
            response = await sess.exec(
                select(Message)
                .where(Message.uuid == uuid)
                .options(selectinload("*"))
                .limit(1)
            )
            return response.one_or_none()

    async def get_message_by_agui_id(
        self, chat_id: uuidpkg.UUID, agui_id: str
    ) -> Message | None:
        """
        Retrieve messages from an AGUI ID.
        """
        async with self._db.session(False) as sess:
            response = await sess.exec(
                select(Message)
                .where(Message.chat_id == chat_id, Message.agui_id == agui_id)
                .options(selectinload("*"))
                .limit(1)
            )
            return response.one_or_none()

    async def get_tool_call_by_agui_id(
        self, message_uuid: uuidpkg.UUID, agui_id: str
    ) -> MessageToolCall | None:
        """
        Retrieves tool call by AGUI / ToolCall ID
        """
        async with self._db.session(False) as sess:
            response = await sess.exec(
                select(MessageToolCall)
                .where(
                    MessageToolCall.message_uuid == message_uuid,
                    MessageToolCall.agui_id == agui_id,
                )
                .options(selectinload("*"))
                .limit(1)
            )
            return response.one_or_none()

    async def get_chat_messages(self, chat_id: uuidpkg.UUID) -> Sequence[Message]:
        """
        Retrieve all messages from the chat.
        """
        async with self._db.session() as sess:
            response = await sess.exec(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at)  # type: ignore[arg-type]
                .options(selectinload("*"))
            )
            return response.all()

    async def get_last_messages(
        self, chat_ids: list[uuidpkg.UUID]
    ) -> dict[uuidpkg.UUID, Message]:
        """
        Retrieve last messages from each chat in the list.
        """
        if not chat_ids:
            return {}

        async with self._db.session() as sess:
            result_dict = {}

            # For each chat, get the latest message
            # This approach avoids the GROUP BY error and is compatible with both SQLite and PostgreSQL
            for chat_id in chat_ids:
                response = await sess.exec(
                    select(Message)
                    .where(Message.chat_id == chat_id)
                    .order_by(desc(Message.created_at))  # type: ignore[arg-type]
                    .options(selectinload("*"))
                    .limit(1)
                )
                message = response.first()
                if message:
                    result_dict[chat_id] = message

            return result_dict
