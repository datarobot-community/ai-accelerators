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
from typing import Any, Sequence, cast

from sqlalchemy import Column, DateTime, ForeignKey, UniqueConstraint
from sqlmodel import Field, Index, SQLModel, select

from app.db import DBCtx
from app.users.user import User

logger = logging.getLogger(__name__)


class ChatBase(SQLModel):
    name: str = Field(default="New Chat")
    thread_id: str | None = Field(default=None)
    user_uuid: uuidpkg.UUID | None = Field(
        default=None,
        sa_column=Column(
            "user", ForeignKey("user.uuid", ondelete="CASCADE"), index=True
        ),
    )

    # Don't want two users to step on each other's toes.
    __table_args__ = (
        UniqueConstraint("thread_id", "user", name="uq_thread_id_user"),
        Index("ix_thread_id_user", "thread_id", "user"),
    )

    def dump_json_compatible(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.model_dump_json()))


class Chat(ChatBase, table=True):
    uuid: uuidpkg.UUID = Field(
        default_factory=uuidpkg.uuid4, primary_key=True, unique=True
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    def dump_json_compatible(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(self.model_dump_json()))


class ChatCreate(ChatBase):
    """
    Schema for creating a new chat.
    """


class ChatRepository:
    """
    Chat repository class to handle chat-related database operations.
    """

    def __init__(self, db: DBCtx):
        self._db = db

    async def create_chat(self, chat_data: ChatCreate) -> Chat:
        chat = Chat(**chat_data.model_dump())

        async with self._db.session(writable=True) as session:
            session.add(chat)
            await session.commit()
            await session.refresh(chat)
            return chat

    async def get_chat(self, uuid: uuidpkg.UUID) -> Chat:
        async with self._db.session() as sess:
            response = await sess.exec(select(Chat).where(Chat.uuid == uuid).limit(1))
            return response.one()

    async def get_chat_by_thread_id(
        self, user_uuid: uuidpkg.UUID, thread_id: str
    ) -> Chat | None:
        async with self._db.session() as sess:
            query = (
                select(Chat)
                .where(Chat.user_uuid == user_uuid, Chat.thread_id == thread_id)
                .limit(1)
            )
            response = await sess.exec(query)
            return response.one_or_none()

    async def get_all_chats(self, user: User | None) -> Sequence[Chat]:
        query = select(Chat)
        if user:
            query = query.where(Chat.user_uuid == user.uuid)
        async with self._db.session() as sess:
            response = await sess.exec(query)
            return response.all()

    async def update_chat_name(self, uuid: uuidpkg.UUID, name: str) -> Chat | None:
        async with self._db.session(writable=True) as sess:
            response = await sess.exec(select(Chat).where(Chat.uuid == uuid).limit(1))
            chat = response.one_or_none()
            if not chat:
                return None

            chat.name = name
            sess.add(chat)
            await sess.commit()
            await sess.refresh(chat)
            return chat

    async def delete_chat(self, uuid: uuidpkg.UUID) -> Chat | None:
        """
        Delete a chat by UUID.
        The associated messages will be automatically deleted via CASCADE foreign key constraint.
        """
        async with self._db.session(writable=True) as sess:
            response = await sess.exec(select(Chat).where(Chat.uuid == uuid).limit(1))
            chat = response.first()
            if not chat:
                return None

            await sess.delete(chat)
            await sess.commit()
            return chat
