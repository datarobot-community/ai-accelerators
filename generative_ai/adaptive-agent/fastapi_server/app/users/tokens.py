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

from datarobot.auth.identity import Identity as IdentityData
from datarobot.auth.oauth import AsyncOAuthComponent, OAuthToken

from app.users.identity import IdentityRepository, IdentityUpdate

logger = logging.getLogger(__name__)


class NoRefreshToken(Exception):
    """
    Exception raised when there is no refresh token available but the access token is empty or expired
    """


class Tokens:
    """
    An OAuth2 access token manager
    """

    def __init__(
        self,
        oauth: AsyncOAuthComponent,
        identity_repo: IdentityRepository,
        leeway_secs: int = 60,
    ) -> None:
        self._leeway_secs = leeway_secs
        self._oauth = oauth
        self._identity_repo = identity_repo

    async def get_access_token(
        self, identity: IdentityData, scope: str | None = None
    ) -> OAuthToken:
        """
        Get an access token for the given identity

        Assuming that we have multiple replicas of this application we can't have a safe in-memory cache here, because
        every time a replica refresh token, it will be invalidated all previous tokens in other replicas.
        """
        ctx = {
            "identity": identity,
        }

        identity_model = await self._identity_repo.get_identity_by_id(
            identity_id=int(identity.id)
        )

        if identity_model is None:
            raise ValueError(f"Identity with id {identity.id} not found")

        if identity_model.access_token and not identity_model.access_token_expired(
            leeway_secs=self._leeway_secs
        ):
            logger.info("found actual access token", extra=ctx)

            return OAuthToken(
                access_token=identity_model.access_token,
                expires_at=identity_model.access_token_expires_at,
            )

        logger.info("found expired access token, refreshing", extra=ctx)

        token_data = await self._oauth.refresh_access_token(
            provider_id=identity_model.provider_id,
            identity_id=identity_model.provider_identity_id,
            refresh_token=identity_model.refresh_token,
            scope=scope,
        )

        update = IdentityUpdate(
            access_token=token_data.access_token,
            access_token_expires_at=token_data.expires_at,
        )

        if token_data.refresh_token:
            update.refresh_token = token_data.refresh_token

        if not identity_model.id:
            raise ValueError(f"Identity must have id {identity.id}")

        await self._identity_repo.update_identity(
            identity_id=identity_model.id, update=update
        )

        return token_data

    async def validate_token(self, identity: IdentityData) -> tuple[bool, int | None]:
        """
        Validate if the token for an identity is still valid by forcing a refresh.

        Unlike get_access_token, this always contacts the OAuth provider to verify
        the authorization hasn't been revoked.

        Returns:
            (is_valid, error_status_code) - status_code is None if valid or if error had no HTTP status
        """
        identity_model = await self._identity_repo.get_identity_by_id(
            identity_id=int(identity.id)
        )

        if identity_model is None:
            return (False, None)

        try:
            # Force a refresh to verify the authorization is still valid
            token_data = await self._oauth.refresh_access_token(
                provider_id=identity_model.provider_id,
                identity_id=identity_model.provider_identity_id,
                refresh_token=identity_model.refresh_token,
            )
        except Exception as e:
            # Try to extract HTTP status code from the exception
            status_code = getattr(e, "status_code", None)
            if status_code is None:
                response = getattr(e, "response", None)
                if response:
                    status_code = getattr(response, "status_code", None)

            logger.warning(
                "Token validation failed",
                extra={
                    "identity_id": identity.id,
                    "status_code": status_code,
                    "error": str(e),
                },
            )
            return (False, status_code)

        # OAuth refresh succeeded - persist the new tokens (important for rotating refresh tokens)
        update = IdentityUpdate(
            access_token=token_data.access_token,
            access_token_expires_at=token_data.expires_at,
        )

        if token_data.refresh_token:
            update.refresh_token = token_data.refresh_token

        if identity_model.id:
            await self._identity_repo.update_identity(
                identity_id=identity_model.id, update=update
            )
        else:
            raise ValueError(f"Identity must have id {identity.id}")

        return (True, None)
