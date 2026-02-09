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
from enum import Enum
from typing import TYPE_CHECKING

from datarobot.auth.authlib.oauth import AsyncOAuth as AuthlibOAuth
from datarobot.auth.authlib.oauth import OAuthProviderConfig
from datarobot.auth.datarobot.oauth import AsyncOAuth as DatarobotOAuth
from datarobot.auth.oauth import AsyncOAuthComponent

from app.users.auth import box_user_info_mapper
from app.users.identity import ProviderType

if TYPE_CHECKING:
    from app import Config

logger = logging.getLogger(__name__)


class OAuthImpl(str, Enum):
    """
    OAuth implementations supported by the application template.
    """

    AUTHLIB = "authlib"
    DATAROBOT = "datarobot"

    @classmethod
    def all(cls) -> list[str]:
        """
        Returns a list of all available OAuth implementations.
        """
        return [impl.value for impl in OAuthImpl]


def get_oauth(config: "Config") -> AsyncOAuthComponent:
    if config.oauth_impl == OAuthImpl.DATAROBOT:
        if not config.datarobot_oauth_providers:
            logger.warning(
                "No OAuth providers configured for the DataRobot implementation. "
                "Use the `DATAROBOT_OAUTH_PROVIDERS` environment variable to set them up."
            )

        return DatarobotOAuth(
            config.datarobot_oauth_providers,
            datarobot_endpoint=config.datarobot_endpoint,
            datarobot_api_token=config.datarobot_api_token,
        )

    if config.oauth_impl == OAuthImpl.AUTHLIB:
        provider_configs: list[OAuthProviderConfig] = []

        if config.google_client_id and config.google_client_secret:
            provider_configs.append(
                OAuthProviderConfig(
                    id=ProviderType.GOOGLE.value,
                    client_id=config.google_client_id,
                    client_secret=config.google_client_secret,
                    scope="openid email profile https://www.googleapis.com/auth/drive.readonly",
                    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                    authorize_params={
                        "access_type": "offline",
                        "prompt": "consent",  # TODO: can we remove the prompt param here?
                    },
                )
            )

        if config.box_client_id and config.box_client_secret:
            provider_configs.append(
                OAuthProviderConfig(
                    id=ProviderType.BOX.value,
                    client_id=config.box_client_id,
                    client_secret=config.box_client_secret,
                    scope="root_readwrite",
                    authorize_url="https://account.box.com/api/oauth2/authorize",
                    access_token_url="https://api.box.com/oauth2/token",
                    userinfo_endpoint="https://api.box.com/2.0/users/me",
                    userinfo_mapper=box_user_info_mapper,
                )
            )

        if config.microsoft_client_id and config.microsoft_client_secret:
            provider_configs.append(
                OAuthProviderConfig(
                    id=ProviderType.MICROSOFT.value,
                    client_id=config.microsoft_client_id,
                    client_secret=config.microsoft_client_secret,
                    scope="https://graph.microsoft.com/Files.ReadWrite.All offline_access",
                    authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                    access_token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
                )
            )

        if not provider_configs:
            logger.warning(
                "No OAuth providers configured for the authlib implementation. "
                "Use the `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, "
                "`MICROSOFT_CLIENT_ID`, and `MICROSOFT_CLIENT_SECRET` environment variables to set them up."
            )

        return AuthlibOAuth()

    raise ValueError(
        f"Unsupported OAuth implementation: {config.oauth_impl}. "
        f"Available implementations: {', '.join(OAuthImpl.all())}."
    )
