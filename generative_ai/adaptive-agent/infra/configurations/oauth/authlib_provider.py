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
from typing import Final

import pulumi
import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME

# these configs are expected in the web application
DATAROBOT_OAUTH_PROVIDERS: Final[str] = "DATAROBOT_OAUTH_PROVIDERS"
GOOGLE_CLIENT_ID: Final[str] = "GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET: Final[str] = "GOOGLE_CLIENT_SECRET"
BOX_CLIENT_ID: Final[str] = "BOX_CLIENT_ID"
BOX_CLIENT_SECRET: Final[str] = "BOX_CLIENT_SECRET"

google_client_id = os.environ.get(GOOGLE_CLIENT_ID)
google_client_secret = os.environ.get(GOOGLE_CLIENT_SECRET)
box_client_id = os.environ.get(BOX_CLIENT_ID)
box_client_secret = os.environ.get(BOX_CLIENT_SECRET)

app_runtime_parameters = []

if google_client_id and google_client_secret:
    pulumi.info(
        "Google OAuth credentials found, adding to application runtime parameters."
    )
    pulumi.export("Google Client ID", google_client_id)

    google_client_secret_cred = datarobot.ApiTokenCredential(
        f"[{PROJECT_NAME}] Agent Application Google Client",
        args=datarobot.ApiTokenCredentialArgs(
            api_token=str(google_client_secret),
        ),
    )

    app_runtime_parameters += [
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            type="string",
            key=GOOGLE_CLIENT_ID,
            value=google_client_id,
        ),
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            type="credential",
            key=GOOGLE_CLIENT_SECRET,
            value=google_client_secret_cred.id,
        ),
    ]

if box_client_id and box_client_secret:
    pulumi.info("Box credentials found, adding to application runtime parameters.")
    pulumi.export("Box Client ID", box_client_id)

    box_client_secret_cred = datarobot.ApiTokenCredential(
        f"[{PROJECT_NAME}] Agent Application Box Client",
        args=datarobot.ApiTokenCredentialArgs(
            api_token=str(box_client_secret),
        ),
    )

    app_runtime_parameters += [
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            type="string",
            key=BOX_CLIENT_ID,
            value=box_client_id,
        ),
        datarobot.ApplicationSourceRuntimeParameterValueArgs(
            type="credential",
            key=BOX_CLIENT_SECRET,
            value=box_client_secret_cred.id,
        ),
    ]
