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
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator

from ag_ui.core import RunAgentInput
from ag_ui.encoder import EventEncoder
from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from datarobot.core import getenv
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.ag_ui.translate import ExtendedBaseMessage, translate_messages
from app.auth.ctx import get_agent_headers, must_get_auth_ctx
from app.chats import Chat, ChatBase, ChatRepository
from app.deps import Deps
from app.messages import (
    MessageRepository,
)
from app.users.user import User, UserRepository

logger = logging.getLogger(__name__)
chat_router = APIRouter(tags=["Chat"])

agent_deployment_token = getenv("AGENT_DEPLOYMENT_TOKEN") or "dummy"
AGENT_MODEL_NAME = "web-agents"


SYSTEM_PROMPT = "You are a helpful assistant. Answer the user's provided question."


async def _get_current_user(user_repo: "UserRepository", user_id: int) -> "User":
    current_user = await user_repo.get_user(user_id=user_id)
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    return current_user


class ChatWithUpdateTime(ChatBase):
    created_at: datetime
    update_time: datetime


class ChatWithUpdateTimeAndMessages(ChatBase):
    created_at: datetime
    update_time: datetime
    messages: list[ExtendedBaseMessage]


@chat_router.get("/chat")
async def get_list_of_chats(
    request: Request, auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx)
) -> list[ChatWithUpdateTime]:
    """Return list of all chats"""
    current_user = await _get_current_user(
        request.app.state.deps.user_repo, int(auth_ctx.user.id)
    )

    chat_repo: ChatRepository = request.app.state.deps.chat_repo
    message_repo: MessageRepository = request.app.state.deps.message_repo

    chats = await chat_repo.get_all_chats(current_user)
    chat_ids = [chat.uuid for chat in chats]
    last_messages = await message_repo.get_last_messages(chat_ids)

    chats_with_update_time = []
    for chat in chats:
        last_message = last_messages.get(chat.uuid)
        chats_with_update_time.append(
            ChatWithUpdateTime(
                update_time=last_message.created_at
                if last_message
                else chat.created_at,
                **chat.model_dump(),
            )
        )

    return chats_with_update_time


@chat_router.get("/chat/{thread_id}")
async def get_chat(
    request: Request,
    thread_id: str,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> ChatWithUpdateTimeAndMessages:
    """Return a chat and its messages."""
    current_user = await _get_current_user(
        request.app.state.deps.user_repo, int(auth_ctx.user.id)
    )

    chat_repo: ChatRepository = request.app.state.deps.chat_repo
    message_repo: MessageRepository = request.app.state.deps.message_repo

    chat = await chat_repo.get_chat_by_thread_id(current_user.uuid, thread_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="chat not found"
        )

    messages = list(await message_repo.get_chat_messages(chat.uuid))
    if messages:
        update_time = max(m.created_at for m in messages)
    else:
        update_time = chat.created_at

    extended_messages = list(translate_messages(messages))

    return ChatWithUpdateTimeAndMessages(
        update_time=update_time, messages=extended_messages, **chat.model_dump()
    )


class RenameChatRequst(BaseModel):
    name: str


@chat_router.patch("/chat/{thread_id}")
async def update_chat(
    request: Request,
    rename_request: RenameChatRequst,
    thread_id: str,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> Chat:
    """Updates chat name."""
    current_user = await _get_current_user(
        request.app.state.deps.user_repo, int(auth_ctx.user.id)
    )
    chat_repo: ChatRepository = request.app.state.deps.chat_repo

    chat = await chat_repo.get_chat_by_thread_id(current_user.uuid, thread_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="chat not found"
        )

    await chat_repo.update_chat_name(chat.uuid, rename_request.name)

    return chat


@chat_router.delete("/chat/{thread_id}")
async def delete_chat(
    request: Request,
    thread_id: str,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> Chat:
    """Deletes a chat."""
    current_user = await _get_current_user(
        request.app.state.deps.user_repo, int(auth_ctx.user.id)
    )
    chat_repo: ChatRepository = request.app.state.deps.chat_repo

    chat = await chat_repo.get_chat_by_thread_id(current_user.uuid, thread_id)

    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="chat not found"
        )

    await chat_repo.delete_chat(chat.uuid)

    return chat


@dataclass
class NoMoreEvents:
    pass


@chat_router.post("/chat")
async def create_chat_messages(
    request: Request,
    run_input: RunAgentInput,
    auth_ctx: AuthCtx[Metadata] = Depends(must_get_auth_ctx),
) -> StreamingResponse:
    """Send a message to a new or existing thread."""
    current_user = await _get_current_user(
        request.app.state.deps.user_repo, int(auth_ctx.user.id)
    )
    deps: Deps = request.app.state.deps

    # Create an event encoder to properly format SSE events
    encoder = EventEncoder(accept=request.headers.get("accept") or "")
    agent_headers = get_agent_headers(request, auth_ctx, deps.config.session_secret_key)

    stream = deps.stream_manager.run(run_input, current_user.uuid, agent_headers)

    async def run_agent_in_background() -> AsyncIterator[str]:
        async for event in await stream:
            yield encoder.encode(event)

    headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    return StreamingResponse(
        run_agent_in_background(),
        media_type=encoder.get_content_type(),
        headers=headers,
    )
