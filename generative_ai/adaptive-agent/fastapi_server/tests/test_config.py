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
from unittest.mock import patch

from app import Config


def test__config__load_env_vars() -> None:
    # mix of prefixed and unprefixed env vars
    env_vars = dict(
        # The format of secrets in the DataRobot Custom App env
        MLOPS_RUNTIME_PARAM_SESSION_SECRET_KEY='{"type":"credential","payload":{"credentialType":"api_token","apiToken":"test-secret-key"}}',
        MLOPS_RUNTIME_PARAM_DATAROBOT_OAUTH_PROVIDERS='["abc", "123"]',
        DATAROBOT_ENDPOINT="https://api.test.datarobot.com",
        DATAROBOT_API_TOKEN="local-test-datarobot-api-key",
    )

    with patch.dict(os.environ, env_vars, clear=True):
        config = Config()

        assert config.session_secret_key == "test-secret-key"
        assert config.datarobot_oauth_providers
        assert len(config.datarobot_oauth_providers) == 2
        assert config.datarobot_endpoint == "https://api.test.datarobot.com"
        assert config.datarobot_api_token == "local-test-datarobot-api-key"
