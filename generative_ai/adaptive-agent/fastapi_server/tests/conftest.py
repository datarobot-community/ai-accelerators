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

import os
from datetime import UTC, datetime, timedelta
from typing import AsyncGenerator, Awaitable, Callable, Generator, TypeVar
from unittest.mock import AsyncMock

import pytest
from datarobot.auth.datarobot.oauth import AsyncOAuth
from datarobot.auth.oauth import OAuthFlowSession, OAuthToken
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app import create_app
from app.ag_ui.stream_manager import AGUIStreamManager
from app.auth.api_key import APIKeyValidator, DRUser
from app.chats import ChatRepository
from app.config import Config
from app.db import DBCtx
from app.deps import Deps, create_deps
from app.messages import MessageRepository
from app.users.identity import AuthSchema, Identity, IdentityCreate, IdentityRepository
from app.users.tokens import Tokens
from app.users.user import User, UserCreate, UserRepository


async def migrate_tables_to_db(db: DBCtx) -> None:
    async with db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@pytest.fixture()
def config() -> Config:
    return Config(
        session_secret_key="test-session-secret-key",
        session_https_only=False,
        database_uri="sqlite+aiosqlite:///:memory:",
        datarobot_endpoint="https://api.test.datarobot.com",
        datarobot_api_token="test-datarobot-api-key",
    )


@pytest.fixture
def deps(config: Config) -> Deps:
    """
    Dependency function to provide the necessary dependencies for the FastAPI app.
    Most of the dependencies are mocked to avoid unnecessary complexity in some tests.
    """
    return Deps(
        config=config,
        chat_repo=AsyncMock(spec=ChatRepository),
        message_repo=AsyncMock(spec=MessageRepository),
        identity_repo=AsyncMock(spec=IdentityRepository),
        user_repo=AsyncMock(spec=UserRepository),
        tokens=AsyncMock(spec=Tokens),
        auth=AsyncMock(spec=AsyncOAuth),
        api_key_validator=AsyncMock(spec=APIKeyValidator),
        db=AsyncMock(spec=DBCtx),
        stream_manager=AsyncMock(spec=AGUIStreamManager),
    )


@pytest.fixture
def webapp(config: Config, deps: Deps) -> FastAPI:
    """
    Create a FastAPI app instance with the provided configuration.
    """
    app = create_app(config=config, deps=deps)
    return app


@pytest.fixture
def client(webapp: FastAPI) -> Generator[TestClient, None, None]:
    """
    Create a test client for the FastAPI app.

    Note: This client is not authenticated by default. For authenticated endpoints,
    use the `authenticated_client` fixture instead.
    """
    with TestClient(webapp) as client:
        yield client


@pytest.fixture
def simple_client(config: Config, deps: Deps) -> TestClient:
    """
    Create a simple test client for the FastAPI app without authentication.

    Use this fixture for testing endpoints that don't require authentication.
    For authenticated endpoints, use the `authenticated_client` fixture instead.
    """
    app = create_app(config=config, deps=deps)
    # Explicitly set the state since lifespan may not work correctly in TestClient
    app.state.deps = deps
    return TestClient(app)


T = TypeVar("T")


def dep(value: T) -> Callable[[Request], Awaitable[T]]:
    """
    A convenient wrapper to turn a mocked value into a FastAPI.Deps() function
    """

    async def mock_deps(request: Request) -> T:
        return value

    return mock_deps


@pytest.fixture(scope="session", autouse=True)
def clear_environment() -> Generator[None, None, None]:
    """Clear all environment variables at the start of the testing session."""
    # Store original environment
    original_env = dict(os.environ)

    # Clear all environment variables
    os.environ.clear()

    yield

    # Restore original environment after all tests complete
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def make_app_user() -> Callable[..., User]:
    """Factory fixture to create AppUser instances with custom data."""
    user_counter = 0

    def _make_user(
        email: str = "test@example.com",
        first_name: str = "Alex",
        last_name: str = "Smith",
    ) -> User:
        nonlocal user_counter
        user_counter += 1
        return User(
            id=user_counter,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

    return _make_user


@pytest.fixture
def make_app_identity() -> Callable[[User], Identity]:
    """Factory fixture to create Identity instances for given users."""
    identity_counter = 0

    def _make_identity(user: User) -> Identity:
        nonlocal identity_counter
        identity_counter += 1
        return Identity(
            id=identity_counter,
            type=AuthSchema.OAUTH2,
            user_id=user.id or identity_counter,
            provider_id="google",
            provider_type="google",
            provider_user_id=f"google-user-id-{identity_counter}",
            provider_identity_id=f"provider-identity-id-{identity_counter}",
            access_token="access-token",
            access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
            refresh_token="refresh-token",
            datarobot_org_id="org-id",
            datarobot_tenant_id="tenant-id",
        )

    return _make_identity


class TestAPIKeyValidator:
    """Custom API key validator for tests that maps API keys to users."""

    def __init__(self) -> None:
        self.user_map: dict[str, DRUser] = {}

    def add_user(self, api_key: str, dr_user: DRUser) -> None:
        """Register a user for a specific API key."""
        self.user_map[api_key] = dr_user

    async def validate(self, api_key: str) -> DRUser | None:
        """Return the user for the given API key, or None if not found."""
        return self.user_map.get(api_key)


@pytest.fixture
async def make_authenticated_client(
    config: Config,
) -> AsyncGenerator[Callable[..., Awaitable[TestClient]], None]:
    """
    Factory fixture to create a full unmocked in-memory DB
    authenticated test clients with custom user data.
    """

    # Create a shared test API key validator that can map different API keys to different users
    test_api_key_validator = TestAPIKeyValidator()

    # Create the database dependencies once and share them
    async with create_deps(config) as shared_deps:
        # Replace the api_key_validator with our test version
        shared_deps.api_key_validator = test_api_key_validator  # type: ignore[assignment]

        # Create the app with these shared dependencies
        app = create_app(config=config, deps=shared_deps)
        app.state.deps = shared_deps
        await migrate_tables_to_db(shared_deps.db)

        async def _make_client(
            email: str = "test@datarobot.com",
            first_name: str = "Michael",
            last_name: str = "Smith",
        ) -> TestClient:
            # Create user and identity for this client
            user_create = UserCreate(
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user_repo: UserRepository = shared_deps.user_repo
            user = await user_repo.create_user(user_create)
            if not user.id:
                raise ValueError("User creation failed, no ID assigned.")

            identity_create = IdentityCreate(
                user_id=user.id,
                provider_id="google",
                provider_type="google",
                provider_user_id=f"google-user-id-{user.id}",
                provider_identity_id=f"provider-identity-id-{user.id}",
                access_token="access-token",
                access_token_expires_at=datetime.now(UTC) + timedelta(hours=1),
                refresh_token="refresh-token",
                datarobot_org_id="org-id",
                datarobot_tenant_id="tenant-id",
            )
            identity_repo: IdentityRepository = shared_deps.identity_repo
            identity = await identity_repo.create_identity(identity_create)

            # Create a unique API key for this user
            unique_api_key = f"test-api-key-{user.id}"

            # Create a DRUser representation
            test_dr_user = DRUser(
                id=str(user.id),
                org_id="org-id",
                tenant_id="tenant-id",
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                lang="en",
                feature_flags={},
            )

            # Register this user with the test API key validator
            test_api_key_validator.add_user(unique_api_key, test_dr_user)

            client = TestClient(app)

            # Set up authentication headers with the unique API key
            client.headers.update(
                {
                    "X-DATAROBOT-API-KEY": unique_api_key,
                    "X-USER-EMAIL": user.email,
                }
            )

            # Attach user objects to the client for easy access in tests
            client.user = user  # type: ignore[attr-defined]
            client.dr_user = test_dr_user  # type: ignore[attr-defined]
            client.app_identity = identity  # type: ignore[attr-defined]

            return client

        yield _make_client


@pytest.fixture
def app_user(make_app_user: Callable[..., User]) -> User:
    return make_app_user()


@pytest.fixture
def app_identity(
    app_user: User, make_app_identity: Callable[[User], Identity]
) -> Identity:
    return make_app_identity(app_user)


@pytest.fixture
def authenticated_client(
    config: Config, deps: Deps, app_user: User, app_identity: Identity
) -> TestClient:
    """
    Create an authenticated test client with a default user session.

    This client automatically includes:
    - Authentication headers (X-DATAROBOT-API-KEY, X-USER-EMAIL)
    - Mocked user and identity data
    - Properly configured deps for authenticated endpoints

    Use this fixture for testing endpoints that require authentication.
    """
    app = create_app(config=config, deps=deps)
    app.state.deps = deps

    # Create a test client with authentication headers
    client = TestClient(app)

    # Set up authentication headers that will be used by get_datarobot_ctx
    client.headers.update(
        {
            "X-DATAROBOT-API-KEY": "test-api-key",
            "X-USER-EMAIL": app_user.email,
        }
    )

    # Mock the API key validator to return our test user
    test_dr_user = DRUser(
        id=str(app_user.id),
        org_id="test-org-id",
        tenant_id="test-tenant-id",
        email=app_user.email,
        first_name=app_user.first_name,
        last_name=app_user.last_name,
        lang="en",
        feature_flags={},
    )

    # Configure the mocked API key validator
    deps.api_key_validator.validate = AsyncMock(return_value=test_dr_user)  # type: ignore[method-assign]

    # Mock the user and identity repositories to return our test data
    deps.user_repo.get_user = AsyncMock(return_value=app_user)  # type: ignore[method-assign]
    deps.identity_repo.get_by_external_user_id = AsyncMock(return_value=app_identity)  # type: ignore[method-assign]
    deps.identity_repo.upsert_identity = AsyncMock(return_value=app_identity)  # type: ignore[method-assign]

    # Attach user objects to the client for easy access in tests
    client.app_user = app_user  # type: ignore[attr-defined]
    client.dr_user = test_dr_user  # type: ignore[attr-defined]
    client.app_identity = app_identity  # type: ignore[attr-defined]

    return client


@pytest.fixture
def oauth_token() -> OAuthToken:
    ttl = 3600  # 1 hour in seconds

    return OAuthToken(
        access_token="sk-access-token",
        token_type="Bearer",
        expires_in=ttl,
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
        scope="openid email profile",
        refresh_token="rt-refresh-token",
    )


@pytest.fixture
def oauth_sess() -> OAuthFlowSession:
    return OAuthFlowSession(
        provider_id="google",
        authorization_url="https://auth.test.com/authorize",
        redirect_uri="https://app.test.com/callback",
        state="test-state",
    )


@pytest.fixture
def dr_user() -> DRUser:
    return DRUser(
        id="61092ffc5f851383dd782b30",
        org_id="57e43914d75f160c3bac26f6",
        tenant_id="7a88e3bd-c606-4f16-8c7b-ccde5dd413f1",
        email="angela.martins@example.com",
        first_name="Angela",
        last_name="Martins",
        lang="en",
        feature_flags={
            "ENABLE_FEATURE_ONE": True,
            "ENABLE_FEATURE_TWO": False,
        },
    )


@pytest.fixture
async def db_deps(config: Config) -> AsyncGenerator[Deps, None]:
    """
    Dependency function to provide the necessary dependencies for the FastAPI app with a real database connection.
    This is useful for tests that require actual database interactions but want mocked auth components.
    """
    config.database_uri = "sqlite+aiosqlite:///:memory:"

    # create_deps returns an async context manager, so enter it to get the Deps instance
    async with create_deps(config) as deps_ctx:
        # Replace auth-related components with mocks for easier testing
        deps_ctx.auth = AsyncMock(spec=AsyncOAuth)
        deps_ctx.api_key_validator = AsyncMock(spec=APIKeyValidator)
        deps_ctx.tokens = AsyncMock(spec=Tokens)

        await migrate_tables_to_db(deps_ctx.db)
        yield deps_ctx


@pytest.fixture
def db_webapp(config: Config, db_deps: Deps) -> FastAPI:
    """
    Create a FastAPI app instance with the provided configuration and database dependencies.
    """
    app = create_app(config=config, deps=db_deps)
    app.state.deps = db_deps
    return app
