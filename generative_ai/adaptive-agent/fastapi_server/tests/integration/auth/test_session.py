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

from datarobot.auth.oauth import OAuthFlowSession
from fastapi import Request
from fastapi.testclient import TestClient

from app.auth.session import restore_oauth_session, store_oauth_sess


def test__oauth_sess__storing(client: TestClient, oauth_sess: OAuthFlowSession) -> None:
    state = "test_state"

    req = AsyncMock(spec=Request)
    req.session = {}

    sess = restore_oauth_session(req, state)
    assert not sess

    store_oauth_sess(req, oauth_sess)
    sess = restore_oauth_session(req, oauth_sess.state)
    assert sess
