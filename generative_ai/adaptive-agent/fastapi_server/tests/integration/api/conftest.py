# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from datarobot.auth.identity import Identity
from datarobot.auth.oauth import OAuthData, OAuthProvider, OAuthToken, Profile
from datarobot.auth.session import AuthCtx
from datarobot.auth.typing import Metadata
from datarobot.auth.users import User


@pytest.fixture
def auth_ctx() -> AuthCtx[Metadata]:
    return AuthCtx[Metadata](
        user=User(
            id="1",
            email="test@datarobot.com",
        ),
        identities=[
            Identity(
                id="1",
                type="oauth2",
                provider_type="google",
                provider_user_id="google-user-id",
            )
        ],
    )


@pytest.fixture
def oauth_provider() -> OAuthProvider:
    return OAuthProvider(
        id="google",
        type="google",
        name="Google",
        client_id="google-client-id",
        client_secret="google-client-secret",
        authorization_url="https://accounts.google.com/o/oauth2/auth",
        token_url="https://oauth2.googleapis.com/token",
        user_info_url="https://www.googleapis.com/oauth2/v3/userinfo",
    )


@pytest.fixture
def dr_oauth_data(oauth_token: OAuthToken, oauth_provider: OAuthProvider) -> OAuthData:
    oauth_token.refresh_token = None

    return OAuthData(
        authorization_id="authz_id",
        token_data=oauth_token,
        provider=oauth_provider,
        user_profile=Profile(
            id="ext-user-id",
            email="luidgi@example.com",
            email_verified=True,
            first_name="Luidgi",
            last_name="Corleone",
        ),
    )
