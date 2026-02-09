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
import uuid as uuidpkg
from typing import Any, AsyncGenerator

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
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx_sse import connect_sse

from app import Deps, create_app
from app.auth.ctx import AUTH_CTX_HEADER, get_auth_ctx
from app.users.user import User, UserCreate
from tests.conftest import dep


@pytest.fixture
async def test_chat_user(db_deps: Deps) -> User:
    """Create a test user in the database for chat tests."""
    return await db_deps.user_repo.create_user(
        UserCreate(
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )
    )


@pytest.fixture
def test_chat_auth_ctx(test_chat_user: User) -> AuthCtx[Metadata]:
    """Create an auth context for the test user."""
    return AuthCtx(
        user=AuthUser(
            id=str(test_chat_user.id),
            email=test_chat_user.email,
        ),
        identities=[
            Identity(
                id="test-identity-id",
                type="oauth2",
                provider_type="google",
                provider_user_id="google-user-123",
            )
        ],
        metadata={"dr_ctx": {"email": test_chat_user.email}},
    )


@pytest.fixture
def authenticated_chat_webapp(
    db_deps: Deps, test_chat_auth_ctx: AuthCtx[Metadata]
) -> FastAPI:
    """Create a webapp with auth context override for chat tests."""
    webapp = create_app(config=db_deps.config, deps=db_deps)
    webapp.dependency_overrides[get_auth_ctx] = dep(test_chat_auth_ctx)
    return webapp


@pytest.fixture
def mock_agent_runner(db_deps: Deps) -> dict[str, Any]:
    """Mock the agent runner to return simple test events and capture call arguments."""
    call_info: dict[str, Any] = {}

    async def agent_run(
        input: RunAgentInput,
        user_id: uuidpkg.UUID,
        headers: dict[str, str],
    ) -> AsyncGenerator[BaseEvent, None]:
        # Capture the arguments for verification
        call_info["headers"] = headers
        call_info["user_id"] = user_id

        async def inner() -> AsyncGenerator[BaseEvent, None]:
            yield RunStartedEvent(thread_id=input.thread_id, run_id=input.run_id)
            yield RunFinishedEvent(
                thread_id=input.thread_id, run_id=input.run_id, result="done"
            )

        return inner()

    db_deps.stream_manager.run = agent_run  # type:ignore[method-assign]
    return call_info


async def test_chat_endpoint_includes_auth_header(
    db_deps: Deps,
    test_chat_user: User,
    authenticated_chat_webapp: FastAPI,
    mock_agent_runner: dict[str, Any],
) -> None:
    """
    Integration test that verifies the chat endpoint passes the authorization
    context header to the agent via stream_manager.run().

    This test verifies that:
    1. The stream_manager.run() is called with the correct user_id
    2. The stream_manager.run() receives headers dict with X-DataRobot-Authorization-Context
    3. The JWT token in the header can be decoded using the application's session secret
    4. The token contains the expected user and identity information
    """

    json = RunAgentInput(
        thread_id="test-thread",
        run_id="test-run",
        state="",
        messages=[UserMessage(id="m1", content="Test message", name="user")],
        tools=[],
        context=[],
        forwarded_props="",
    ).model_dump()

    with TestClient(authenticated_chat_webapp) as client:
        with connect_sse(client, "POST", "/api/v1/chat", json=json) as event_source:
            # Consume the events to allow the agent to be called
            list(event_source.iter_sse())

    # Verify the agent was called with the correct user_id
    assert mock_agent_runner["user_id"] == test_chat_user.uuid, (
        f"Expected agent to be called with user_id={test_chat_user.uuid}, "
        f"but got user_id={mock_agent_runner['user_id']}"
    )

    # Verify the agent was called with headers
    agent_headers = mock_agent_runner["headers"]
    assert agent_headers is not None, "Expected agent to be called with headers dict"
    assert isinstance(agent_headers, dict), (
        f"Expected headers to be a dict, but got {type(agent_headers)}"
    )

    # Verify the auth context header is present in the headers passed to the agent
    assert AUTH_CTX_HEADER in agent_headers, (
        f"Expected {AUTH_CTX_HEADER} in headers passed to agent, "
        f"but got headers: {list(agent_headers.keys())}"
    )

    # Verify the JWT can be decoded with the session secret
    jwt_token = agent_headers[AUTH_CTX_HEADER]
    decoded = jwt.decode(jwt_token, db_deps.config.session_secret_key)
    decoded.validate()

    # Verify it contains user information
    assert "user" in decoded, "JWT should contain user information"
    assert "identities" in decoded, "JWT should contain identities"
    assert decoded["user"]["email"] == test_chat_user.email

    # Verify metadata contains the DataRobot context
    assert "metadata" in decoded, "JWT should contain metadata"
    assert "dr_ctx" in decoded["metadata"], (
        "JWT metadata should contain DataRobot context"
    )
    assert decoded["metadata"]["dr_ctx"]["email"] == test_chat_user.email
