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

from enum import Enum

from pydantic import BaseModel


class ErrorCodes(str, Enum):
    UNKNOWN_ERROR = "unknown_error"
    NOT_AUTHED = "auth:not_authenticated"
    INVALID_OAUTH_STATE = "auth:invalid_state"
    NOT_AUTHORIZED = "auth:not_authorized"
    IDENTITY_NOT_FOUND = "identity:not_found"
    DATAROBOT_USER_ERROR = "identity:datarobot_user_error"


class ErrorSchema(BaseModel):
    """
    A generic error response schema
    """

    code: str
    message: str
