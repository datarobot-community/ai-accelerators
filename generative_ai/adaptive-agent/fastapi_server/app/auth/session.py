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
from typing import Final

from datarobot.auth.oauth import OAuthFlowSession
from fastapi import Request

OAUTH_SESS_KEY_PREFIX: Final[str] = "oauth_sess_"


def get_oauth_sess_key(state: str) -> str:
    return f"{OAUTH_SESS_KEY_PREFIX}{state}"


def store_oauth_sess(request: Request, oauth_sess: OAuthFlowSession) -> None:
    """
    Store an OAuth Flow Session in the backend cookie session.
    Remove all previous, orphaned sessions in order to avoid filling up the session storage with old sessions
    in exceptional situations.
    """
    # clean up all previous OAuth sessions for the current provider ID
    for key in list(request.session.keys()):
        if not key.startswith(OAUTH_SESS_KEY_PREFIX):
            continue

        raw_sess = request.session.get(key, {})
        sess = OAuthFlowSession(**raw_sess)

        if sess.provider_id == oauth_sess.provider_id:
            request.session.pop(key, None)

    # store the new OAuth session for the provider

    oauth_sess_key = get_oauth_sess_key(oauth_sess.state)
    request.session[oauth_sess_key] = oauth_sess.model_dump()


def restore_oauth_session(request: Request, state: str) -> OAuthFlowSession | None:
    """
    Restore the OAuth Flow Session by state. This will remove that session from the backend cookie session.
    """
    oauth_sess = None  # you might open the endpoint directly without properly passing through the whole OAuth flow
    oauth_sess_key = get_oauth_sess_key(state)

    if raw_sess := request.session.pop(oauth_sess_key, {}):  # clean up the session
        oauth_sess = OAuthFlowSession(**raw_sess)

    return oauth_sess
