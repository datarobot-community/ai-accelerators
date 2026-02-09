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

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class UserAppCredentials(BaseSettings):
    """User-specific application credentials."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global credentials instance
_user_credentials: Optional[UserAppCredentials] = None


def get_user_credentials() -> UserAppCredentials:
    """Get the global user credentials instance."""
    global _user_credentials
    if _user_credentials is None:
        _user_credentials = UserAppCredentials()
    return _user_credentials
