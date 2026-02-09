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
from unittest.mock import AsyncMock

import pytest
from fastapi import Request
from fastapi.exceptions import HTTPException

from app import Deps
from app.auth.api_key import DRUser
from app.auth.ctx import AUTH_SESS_KEY, DRAppCtx, get_auth_ctx, get_datarobot_ctx
from app.users.identity import AuthSchema, IdentityCreate, ProviderType
from app.users.user import UserCreate


async def test__get_auth_ctx__new_visit__dr_user(
    db_deps: Deps, dr_user: DRUser
) -> None:
    req = AsyncMock(spec=Request)
    req.session = {}
    req.app.state.deps = db_deps

    db_deps.api_key_validator.validate.return_value = dr_user  # type: ignore[attr-defined]

    dr_ctx = DRAppCtx(api_key="test-scoped-api-key")

    auth_ctx = await get_auth_ctx(req, dr_ctx)

    assert auth_ctx
    assert auth_ctx.user.given_name == dr_user.first_name
    assert auth_ctx.user.family_name == dr_user.last_name
    assert auth_ctx.user.email == dr_user.email

    identity = await db_deps.identity_repo.get_by_user_id(
        ProviderType.DATAROBOT_USER, int(auth_ctx.user.id)
    )

    assert identity
    assert identity.type == AuthSchema.DATAROBOT
    assert identity.provider_type == ProviderType.DATAROBOT_USER
    assert identity.provider_user_id == dr_user.id


async def test__get_auth_ctx__new_visit__ext_email(db_deps: Deps) -> None:
    req = AsyncMock(spec=Request)
    req.session = {}
    req.app.state.deps = db_deps

    email = "test@example.com"
    dr_ctx = DRAppCtx(email=email)

    auth_ctx = await get_auth_ctx(req, dr_ctx)

    assert auth_ctx
    assert auth_ctx.user.email == email

    identity = await db_deps.identity_repo.get_by_user_id(
        ProviderType.EXTERNAL_EMAIL, int(auth_ctx.user.id)
    )

    assert identity
    assert identity.type == AuthSchema.DATAROBOT
    assert identity.provider_type == ProviderType.EXTERNAL_EMAIL
    assert identity.provider_user_id == email


async def test__get_auth_ctx__existing_user__new_identity(
    db_deps: Deps, dr_user: DRUser
) -> None:
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps
    req.session = {}

    app_user = await db_deps.user_repo.create_user(
        UserCreate(email=dr_user.email, first_name="First", last_name="Last")
    )
    assert app_user

    assert app_user.id is not None
    user_id = app_user.id
    dr_user_identity = await db_deps.identity_repo.create_identity(
        IdentityCreate(
            user_id=user_id,
            type=AuthSchema.DATAROBOT,
            provider_id=ProviderType.DATAROBOT_USER,
            provider_type=ProviderType.DATAROBOT_USER,
            provider_user_id=dr_user.id,
        )
    )
    assert dr_user_identity

    dr_ctx = DRAppCtx(email=dr_user.email)

    auth_ctx = await get_auth_ctx(req, dr_ctx)

    assert auth_ctx
    assert int(auth_ctx.user.id) == app_user.id
    assert auth_ctx.user.email == dr_user.email
    assert {i.provider_type for i in auth_ctx.identities} == {
        ProviderType.DATAROBOT_USER.value,
        ProviderType.EXTERNAL_EMAIL.value,
    }

    identity = await db_deps.identity_repo.get_by_user_id(
        ProviderType.EXTERNAL_EMAIL, int(auth_ctx.user.id)
    )

    assert identity
    assert identity.type == AuthSchema.DATAROBOT
    assert identity.provider_type == ProviderType.EXTERNAL_EMAIL
    assert identity.provider_user_id == dr_user.email


async def test__get_auth_ctx__new_visit__empty_dr_ctx(db_deps: Deps) -> None:
    """
    Test the case when neither DataRobot API key nor external email is provided
    (exception case that should not happen to DR deployments, but possible during local dev)
    """
    req = AsyncMock(spec=Request)
    req.session = {}
    req.app.state.deps = db_deps

    with pytest.raises(HTTPException):
        _ = await get_auth_ctx(req, DRAppCtx())


def test__dr_ctx__api_key(db_deps: Deps) -> None:
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps
    req.headers = {
        "X-DATAROBOT-API-KEY": "test_api_key",
    }

    auth = get_datarobot_ctx(req)

    assert auth.api_key
    assert not auth.email


def test__dr_ctx__ext_email(db_deps: Deps) -> None:
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps
    req.headers = {"X-USER-EMAIL": "test@example.com"}

    auth = get_datarobot_ctx(req)

    assert not auth.api_key
    assert auth.email


async def test_session_not_updated_when_dr_context_changes_api_key(
    db_deps: Deps,
) -> None:
    """
    Test that demonstrates the bug: when a user has an active session but their
    X-DATAROBOT-API-KEY header changes to a different user, they should get a new
    session reflecting the new user, but currently they retain the old session.
    """
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps

    # First user - create initial session
    first_dr_user = DRUser(
        id="user1",
        org_id="org1",
        tenant_id="tenant1",
        email="first@example.com",
        first_name="First",
        last_name="User",
        lang="en",
        feature_flags={},
    )

    # Mock API key validator to return first user
    db_deps.api_key_validator.validate.return_value = first_dr_user  # type: ignore[attr-defined]

    # Start with empty session
    req.session = {}

    # Get auth context with first user's API key
    first_dr_ctx = DRAppCtx(api_key="first-user-api-key")
    first_auth_ctx = await get_auth_ctx(req, first_dr_ctx)

    # Verify first session is created correctly
    assert first_auth_ctx is not None
    assert first_auth_ctx.user.email == "first@example.com"
    assert AUTH_SESS_KEY in req.session

    # Store the first session data for comparison
    first_session_data = req.session[AUTH_SESS_KEY].copy()

    # Second user - different API key should create new session
    second_dr_user = DRUser(
        id="user2",
        org_id="org2",
        tenant_id="tenant2",
        email="second@example.com",
        first_name="Second",
        last_name="User",
        lang="en",
        feature_flags={},
    )

    # Mock API key validator to return second user for different API key
    db_deps.api_key_validator.validate.return_value = second_dr_user  # type: ignore[attr-defined]

    # Same request object but with different DR context (new API key)
    second_dr_ctx = DRAppCtx(api_key="second-user-api-key")
    second_auth_ctx = await get_auth_ctx(req, second_dr_ctx)

    # BUG: This assertion was failing because the function returns the cached session
    # instead of validating that the session matches the current DR context
    assert second_auth_ctx is not None
    assert second_auth_ctx.user.email == "second@example.com", (
        f"Expected second user email 'second@example.com', "
        f"but got '{second_auth_ctx.user.email}'. "
        f"This indicates the session was not updated when the DR context changed."
    )

    # The session should be updated to reflect the new user
    current_session_data = req.session[AUTH_SESS_KEY]
    assert current_session_data != first_session_data, (
        "Session data should have changed when DR context changed, "
        "but it remained the same (indicates stale session bug)"
    )


async def test_session_not_updated_when_dr_context_changes_email(
    db_deps: Deps,
) -> None:
    """
    Test that demonstrates the bug with external email context: when a user has an
    active session but their X-USER-EMAIL header changes to a different email,
    they should get a new session reflecting the new user, but currently they
    retain the old session.
    """
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps

    # Start with empty session
    req.session = {}

    # Get auth context with first email
    first_dr_ctx = DRAppCtx(email="first@example.com")
    first_auth_ctx = await get_auth_ctx(req, first_dr_ctx)

    # Verify first session is created correctly
    assert first_auth_ctx is not None
    assert first_auth_ctx.user.email == "first@example.com"
    assert AUTH_SESS_KEY in req.session

    # Store the first session data for comparison
    first_session_data = req.session[AUTH_SESS_KEY].copy()

    # Same request object but with different DR context (new email)
    second_dr_ctx = DRAppCtx(email="second@example.com")
    second_auth_ctx = await get_auth_ctx(req, second_dr_ctx)

    # BUG: This assertion was failing because the function returns the cached session
    # instead of validating that the session matches the current DR context
    assert second_auth_ctx is not None
    assert second_auth_ctx.user.email == "second@example.com", (
        f"Expected second user email 'second@example.com', "
        f"but got '{second_auth_ctx.user.email}'. "
        f"This indicates the session was not updated when the DR context changed."
    )

    # The session should be updated to reflect the new user
    current_session_data = req.session[AUTH_SESS_KEY]
    assert current_session_data != first_session_data, (
        "Session data should have changed when DR context changed, "
        "but it remained the same (indicates stale session bug)"
    )


async def test_session_not_updated_when_switching_between_api_key_and_email(
    db_deps: Deps,
) -> None:
    """
    Test that demonstrates the bug when switching between API key and email auth:
    when a user has a session with API key auth but then the headers change to
    email auth (or vice versa), the session should be updated.
    """
    req = AsyncMock(spec=Request)
    req.app.state.deps = db_deps

    # Create a DR user for API key auth
    dr_user = DRUser(
        id="api_user",
        org_id="org1",
        tenant_id="tenant1",
        email="api@example.com",
        first_name="API",
        last_name="User",
        lang="en",
        feature_flags={},
    )

    # Mock API key validator
    db_deps.api_key_validator.validate.return_value = dr_user  # type: ignore[attr-defined]

    # Start with empty session
    req.session = {}

    # Get auth context with API key
    api_key_dr_ctx = DRAppCtx(api_key="test-api-key")
    api_key_auth_ctx = await get_auth_ctx(req, api_key_dr_ctx)

    # Verify API key session is created correctly
    assert api_key_auth_ctx is not None
    assert api_key_auth_ctx.user.email == "api@example.com"
    assert AUTH_SESS_KEY in req.session

    # Store the API key session data for comparison
    api_key_session_data = req.session[AUTH_SESS_KEY].copy()

    # Now switch to email auth (different email than the API user)
    email_dr_ctx = DRAppCtx(email="email@example.com")
    email_auth_ctx = await get_auth_ctx(req, email_dr_ctx)

    # BUG: This assertion was failing because the function returns the cached session
    # instead of recognizing that the auth method/user has changed
    assert email_auth_ctx is not None
    assert email_auth_ctx.user.email == "email@example.com", (
        f"Expected email user 'email@example.com', "
        f"but got '{email_auth_ctx.user.email}'. "
        f"This indicates the session was not updated when switching from API key to email auth."
    )

    # The session should be updated to reflect the new auth method and user
    current_session_data = req.session[AUTH_SESS_KEY]
    assert current_session_data != api_key_session_data, (
        "Session data should have changed when switching from API key to email auth, "
        "but it remained the same (indicates stale session bug)"
    )
