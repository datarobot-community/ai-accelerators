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
from urllib.parse import urljoin

import httpx
from datarobot.auth.oauth import Profile
from fastapi import status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

dr_api_key_schema = HTTPBearer(
    scheme_name="DataRobot API Key",
    description="DataRobot API Key for authentication. "
    "The key should be passed in the `Authorization` header as `Bearer <api_key>`.",
)


class DRUser(BaseModel):
    """
    Represents a DataRobot user.
    This is a placeholder for the actual user model.
    """

    id: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    org_id: str
    tenant_id: str | None = None
    lang: str | None = Field("en")
    feature_flags: dict[str, bool | None] = Field(default_factory=lambda: {})

    @classmethod
    def from_raw(cls, raw: dict[str, str]) -> "DRUser":
        return cls(
            id=raw.get("uid", raw.get("id", None)),
            email=raw.get("email"),
            first_name=raw.get("firstName", raw.get("first_name")),
            last_name=raw.get("lastName", raw.get("last_name")),
            org_id=raw.get("orgId", raw.get("org_id")),
            tenant_id=raw.get("tenantId", raw.get("tenant_id", None)),
            feature_flags=raw.get("permissions", {}),
            lang=raw.get("language", "en"),
        )

    @property
    def tracing_ctx(self) -> dict[str, str]:
        """
        Returns user information to be used as observability context.
        """
        return {
            "user_id": self.id,
            "org_id": self.org_id,
            "tenant_id": self.tenant_id or "",
        }

    def to_profile(self) -> Profile:
        return Profile(
            id=self.id,
            email=self.email,
            email_verified=True,
            name=f"{self.first_name or ''} {self.last_name or ''}".strip(),
            first_name=self.first_name,
            last_name=self.last_name,
            picture=None,  # DataRobot API does not provide a profile picture URL
            locale=self.lang,
            metadata=dict(
                org_id=self.org_id,
                tenant_id=self.tenant_id,
                feature_flags=self.feature_flags,
            ),
        )


class APIKeyValidator:
    """
    Validates the API key from the request headers.
    The DataRobot Client doesn't have methods to do the validation, so we do it here.
    """

    def __init__(
        self, datarobot_endpoint: str, timeout_secs: float | None = 5.0
    ) -> None:
        self._datarobot_endpoint = datarobot_endpoint
        self._profile_url = urljoin(self._datarobot_endpoint, "/api/v2/account/info/")

        self._timeout_secs = timeout_secs

    async def validate(self, api_key: str) -> DRUser | None:
        """
        Validates the API key from the request headers.
        Raises HTTPException if the API key is not valid.
        TODO: it makes sense to retry on network errors here / cache the result
        """
        async with httpx.AsyncClient(timeout=self._timeout_secs) as client:
            resp = await client.get(
                self._profile_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                },
                follow_redirects=True,
            )

            if resp.status_code == status.HTTP_401_UNAUTHORIZED:
                logger.debug(
                    "invalid DataRobot API key",
                    extra={"resp_code": resp.status_code, "resp_body": resp.text},
                )
                return None

            if not resp.is_success:
                logger.warning(
                    "failed to validate DataRobot API key",
                    extra={"resp_code": resp.status_code, "resp_body": resp.text},
                )
                return None

            dr_user = DRUser.from_raw(resp.json())

        logger.info("validated DataRobot API key", extra=dr_user.tracing_ctx)

        return dr_user
