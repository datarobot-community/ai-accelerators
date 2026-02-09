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
import httpx
import pytest
import respx

from app.auth.api_key import APIKeyValidator


@respx.mock
async def test__api_key_validator__valid_key() -> None:
    raw_resp = {
        "uid": "61092ffc5f851383dd782b30",
        "email": "angela.martins@example.com",
        "firstName": "Angela",
        "lastName": "Martins",
        "tenantId": "7a88e3bd-c606-4f16-8c7b-ccde5dd413f1",
        "orgId": "57e43914d75f160c3bac26f6",
        "language": "en",
        "permissions": {
            "ENABLE_FEATURE_ONE": True,
            "ENABLE_FEATURE_TWO": False,
        },
    }

    dr_endpoint = "https://test.datarobot.com"
    api_key = "sk-test-key"

    respx.get(f"{dr_endpoint}/api/v2/account/info/").return_value = httpx.Response(
        200, json=raw_resp
    )

    validator = APIKeyValidator(datarobot_endpoint=dr_endpoint)
    dr_user = await validator.validate(api_key)

    assert dr_user
    assert dr_user.id == raw_resp["uid"]
    assert dr_user.email == raw_resp["email"]
    assert dr_user.org_id == raw_resp["orgId"]


@pytest.mark.parametrize(
    "resp_code",
    [
        401,
        500,
        502,
    ],
)
@respx.mock
async def test__api_key_validator__invalid_key(resp_code: int) -> None:
    dr_endpoint = "https://test.datarobot.com"
    api_key = "sk-test-key"

    respx.get(f"{dr_endpoint}/api/v2/account/info/").return_value = httpx.Response(
        resp_code, content="welp there is an error"
    )

    validator = APIKeyValidator(datarobot_endpoint=dr_endpoint)
    dr_user = await validator.validate(api_key)

    assert not dr_user
