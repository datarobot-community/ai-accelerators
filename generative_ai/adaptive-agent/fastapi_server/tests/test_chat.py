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

"""
Chat API Tests

This module tests the chat endpoints which require authentication.
Uses the `authenticated_client` fixture from conftest.py to automatically
handle authentication setup with a default test user.
"""

import datetime
import uuid as uuidpkg
from typing import Any, AsyncGenerator, Dict, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import litellm.exceptions
import pytest
from ag_ui.core import (
    BaseEvent,
    RunAgentInput,
    RunFinishedEvent,
    RunStartedEvent,
    UserMessage,
)
from authlib.jose import jwt
from datarobot.auth.identity import Identity
from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from datarobot.auth.users import User as AuthUser
from fastapi import Request
from fastapi.testclient import TestClient
from httpx_sse import connect_sse

from app.auth.ctx import (
    AUTH_CTX_HEADER,
    VISITOR_SCOPED_API_KEY_HEADER,
    get_agent_headers,
    get_auth_ctx_header,
)
from app.chats import Chat, ChatRepository
from app.deps import Deps
from app.messages import Message, Role
from app.users.user import User


# Fixtures
@pytest.fixture
def mock_dr_client() -> Generator[MagicMock, None, None]:
    with patch("datarobot.Client") as mock_client:
        client_instance = MagicMock()
        client_instance.token = "test-token"
        client_instance.endpoint = "https://test-endpoint.datarobot.com"
        mock_client.return_value = client_instance
        yield mock_client


@pytest.fixture
def mock_litellm_completion() -> Generator[MagicMock, None, None]:
    """Fixture for successful litellm completion."""
    with patch("litellm.acompletion") as mock_acompletion:

        async def _mock_acompletion(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return {"choices": [{"message": {"role": "assistant", "content": "test"}}]}

        mock_acompletion.side_effect = _mock_acompletion
        yield mock_acompletion


@pytest.fixture
def mock_message_repo() -> AsyncMock:
    """Fixture for mocking message repository with proper return values."""
    return AsyncMock(
        return_value=MagicMock(dump_json_compatible=lambda: {"content": "test"})
    )


@pytest.fixture
def mock_api_connection_error() -> litellm.exceptions.APIConnectionError:
    """Fixture to create a standard APIConnectionError for testing."""
    error_message = '{"message": "Request is too large. The request size is 278284656 bytes and the maximum message size allowed by the server is 11264MB"}'
    return litellm.exceptions.APIConnectionError(
        f"litellm.APIConnectionError: DatarobotException - {error_message}",
        llm_provider="datarobot",
        model="test-model",
    )


@pytest.fixture
def sample_chat() -> Chat:
    """Fixture to create a test chat object."""
    return Chat(
        uuid=uuidpkg.uuid4(),
        thread_id="123",
        name="Test Chat",
        created_at=datetime.datetime(
            2025, 10, 8, 0, 0, 0, 0, tzinfo=datetime.timezone.utc
        ),
    )


@pytest.fixture
def sample_user_message(sample_chat: Chat) -> Message:
    """Fixture to create a test user message object."""
    return Message(
        uuid=uuidpkg.uuid4(),
        chat_id=sample_chat.uuid,
        name="test-model",
        role=Role.USER,
        content="Hello, test!",
    )


@pytest.fixture
def sample_llm_message(sample_chat: Chat) -> Message:
    """Fixture to create a test user message object."""
    return Message(
        uuid=uuidpkg.uuid4(),
        chat_id=sample_chat.uuid,
        name="test-model",
        role=Role.ASSISTANT,
        content="Test response",
        in_progress=True,
    )


@pytest.fixture
def test_user() -> User:
    """Fixture to create a test user object."""
    return User(
        id=5,
        uuid=uuidpkg.uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def sample_auth_ctx(test_user: User) -> AuthCtx[Metadata]:
    """Fixture to create a test auth context."""
    return AuthCtx(
        user=AuthUser(
            id=str(test_user.id),
            email=test_user.email,
        ),
        identities=[
            Identity(
                id="test-identity-id",
                type="oauth2",
                provider_type="google",
                provider_user_id="google-user-123",
            )
        ],
        metadata={"dr_ctx": {"email": test_user.email}},
    )


@pytest.fixture
def session_secret_key() -> str:
    """Fixture for a test session secret key."""
    return "test-secret-key-for-jwt-signing"


# Basic chat tests
async def test_new_chat(
    deps: Deps,
    authenticated_client: TestClient,
    sample_chat: Chat,
) -> None:
    """Test chat completion endpoint with authenticated client."""

    async def agent_run(
        input: RunAgentInput,
        user_id: uuidpkg.UUID,
        headers: Dict[str, str],
    ) -> AsyncGenerator[BaseEvent, None]:
        async def inner() -> AsyncGenerator[BaseEvent, None]:
            yield RunStartedEvent(thread_id=input.thread_id, run_id=input.run_id)
            yield RunFinishedEvent(
                thread_id=input.thread_id, run_id=input.run_id, result=5
            )

        return inner()

    deps.stream_manager.run = agent_run  # type:ignore[method-assign]

    json = RunAgentInput(
        thread_id="123",
        run_id="ignored",
        state="",
        messages=[UserMessage(id="m1", content="MESSAGE", name="user")],
        tools=[],
        context=[],
        forwarded_props="",
    ).model_dump()

    with connect_sse(
        authenticated_client, "POST", "/api/v1/chat", json=json
    ) as event_source:
        responses = list(event_source.iter_sse())

    expected_data = [
        '{"type":"RUN_STARTED","threadId":"123","runId":"ignored"}',
        '{"type":"RUN_FINISHED","threadId":"123","runId":"ignored","result":5}',
    ]

    assert len(responses) == len(expected_data)
    for event, expected in zip(responses, expected_data):
        assert event.event == "message"
        assert event.data == expected


def test_get_chats_with_authentication(
    deps: Deps, authenticated_client: TestClient, sample_chat: Chat
) -> None:
    """Example test showing how easy it is to test authenticated endpoints."""
    with (
        patch.object(
            deps.chat_repo, "get_all_chats", new_callable=AsyncMock
        ) as mock_get_chats,
        patch.object(
            deps.message_repo, "get_last_messages", new_callable=AsyncMock
        ) as mock_get_messages,
    ):
        mock_get_chats.return_value = [sample_chat]
        mock_get_messages.return_value = {}

        response = authenticated_client.get("/api/v1/chat")

        assert response.status_code == 200
        chats = response.json()
        assert chats == [
            {
                "name": "Test Chat",
                "thread_id": "123",
                "user_uuid": None,
                "update_time": "2025-10-08T00:00:00Z",
                "created_at": "2025-10-08T00:00:00Z",
            }
        ]


# Chat deletion tests
def test_delete_chat_success(
    deps: Deps, authenticated_client: TestClient, sample_chat: Chat, test_user: User
) -> None:
    """Test successful chat deletion."""
    with (
        patch.object(
            deps.chat_repo, "delete_chat", new_callable=AsyncMock
        ) as mock_delete,
        patch.object(
            deps.chat_repo, "get_chat_by_thread_id", new_callable=AsyncMock
        ) as mock_get,
        patch.object(deps.user_repo, "get_user", new_callable=AsyncMock) as get_user,
    ):
        get_user.return_value = test_user
        mock_get.return_value = sample_chat
        mock_delete.return_value = sample_chat

        response = authenticated_client.delete("/api/v1/chat/123")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["uuid"] == str(sample_chat.uuid)
        assert response_data["name"] == "Test Chat"

        mock_get.assert_called_once_with(test_user.uuid, "123")
        mock_delete.assert_called_once_with(sample_chat.uuid)


def test_delete_chat_not_found(
    deps: Deps, authenticated_client: TestClient, test_user: User
) -> None:
    """Test chat deletion when chat doesn't exist."""
    with (
        patch.object(
            deps.chat_repo, "delete_chat", new_callable=AsyncMock
        ) as mock_delete,
        patch.object(
            deps.chat_repo, "get_chat_by_thread_id", new_callable=AsyncMock
        ) as mock_get,
        patch.object(deps.user_repo, "get_user", new_callable=AsyncMock) as get_user,
    ):
        get_user.return_value = test_user
        mock_get.return_value = None

        response = authenticated_client.delete("/api/v1/chat/123")

        assert response.status_code == 404
        assert response.json()["detail"] == "chat not found"

        mock_get.assert_called_once_with(test_user.uuid, "123")
        mock_delete.assert_not_called()


# Chat repository tests
async def test_chat_repository_delete_chat_success(sample_chat: Chat) -> None:
    """Test ChatRepository.delete_chat method directly."""
    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.session.return_value.__aenter__.return_value = mock_session

    mock_response = MagicMock()
    mock_response.first.return_value = sample_chat
    mock_session.exec.return_value = mock_response

    repo = ChatRepository(mock_db)
    result = await repo.delete_chat(sample_chat.uuid)

    assert result == sample_chat
    mock_session.exec.assert_called_once()
    mock_session.delete.assert_called_once_with(sample_chat)
    mock_session.commit.assert_called_once()


async def test_chat_repository_delete_chat_not_found() -> None:
    """Test ChatRepository.delete_chat when chat doesn't exist."""
    mock_session = AsyncMock()
    mock_db = MagicMock()
    mock_db.session.return_value.__aenter__.return_value = mock_session

    chat_uuid = uuidpkg.uuid4()

    mock_response = MagicMock()
    mock_response.first.return_value = None
    mock_session.exec.return_value = mock_response

    repo = ChatRepository(mock_db)
    result = await repo.delete_chat(chat_uuid)

    assert result is None
    mock_session.exec.assert_called_once()
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()


def test_get_auth_ctx_header_creates_valid_jwt(
    sample_auth_ctx: AuthCtx[Metadata], session_secret_key: str
) -> None:
    """Test that get_auth_ctx_header creates a valid JWT token in the correct header."""
    result = get_auth_ctx_header(sample_auth_ctx, session_secret_key)

    # Verify header structure
    assert AUTH_CTX_HEADER in result
    assert isinstance(result[AUTH_CTX_HEADER], str)

    # Verify JWT can be decoded
    decoded = jwt.decode(result[AUTH_CTX_HEADER], session_secret_key)
    decoded.validate()

    # Verify payload contains auth context data
    assert decoded["user"]["email"] == sample_auth_ctx.user.email
    assert decoded["user"]["id"] == sample_auth_ctx.user.id
    assert len(decoded["identities"]) == len(sample_auth_ctx.identities)
    assert decoded["metadata"] == sample_auth_ctx.metadata


def test_get_auth_ctx_header_with_custom_algorithm(
    sample_auth_ctx: AuthCtx[Metadata], session_secret_key: str
) -> None:
    """Test that get_auth_ctx_header supports custom JWT algorithms."""
    custom_algorithm = "HS512"
    result = get_auth_ctx_header(
        sample_auth_ctx, session_secret_key, algorithm=custom_algorithm
    )

    # Verify the token can be decoded and validated with the custom algorithm
    token = result[AUTH_CTX_HEADER]
    decoded = jwt.decode(token, session_secret_key)
    decoded.validate()

    # Verify payload is correct
    assert decoded["user"]["email"] == sample_auth_ctx.user.email
    assert decoded["user"]["id"] == sample_auth_ctx.user.id


def test_get_agent_headers_with_api_key(
    sample_auth_ctx: AuthCtx[Metadata], session_secret_key: str
) -> None:
    """Test get_agent_headers includes both auth context and visitor API key headers when API key is present."""

    api_key_value = "my-api-key"
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-datarobot-api-key", api_key_value.encode())],
        }
    )

    headers = get_agent_headers(request, sample_auth_ctx, session_secret_key)

    assert AUTH_CTX_HEADER in headers, "Authorization context header missing"
    assert VISITOR_SCOPED_API_KEY_HEADER in headers, "API key header missing"
    assert headers[VISITOR_SCOPED_API_KEY_HEADER] == api_key_value


def test_get_agent_headers_without_api_key(
    sample_auth_ctx: AuthCtx[Metadata], session_secret_key: str
) -> None:
    """Test get_agent_headers returns only auth context header when API key is absent."""

    request = Request({"type": "http", "headers": []})

    headers = get_agent_headers(request, sample_auth_ctx, session_secret_key)

    assert AUTH_CTX_HEADER in headers
    assert VISITOR_SCOPED_API_KEY_HEADER not in headers
    assert len(headers) == 1, "Unexpected extra headers returned"


def test_get_agent_headers_with_empty_api_key(
    sample_auth_ctx: AuthCtx[Metadata], session_secret_key: str
) -> None:
    """Empty (falsy) API key header value should be ignored."""

    # Header present but empty string value
    request = Request(
        {
            "type": "http",
            "headers": [(b"x-datarobot-api-key", b"")],
        }
    )
    headers = get_agent_headers(request, sample_auth_ctx, session_secret_key)

    assert AUTH_CTX_HEADER in headers
    assert VISITOR_SCOPED_API_KEY_HEADER not in headers, (
        "Empty API key value should not be propagated"
    )
    assert len(headers) == 1
