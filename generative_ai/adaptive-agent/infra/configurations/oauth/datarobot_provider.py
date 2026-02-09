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
import json
import os
from typing import Final

import pulumi
import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.pulumi import export
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME

# these configs are expected in the web application
DATAROBOT_OAUTH_PROVIDERS: Final[str] = "DATAROBOT_OAUTH_PROVIDERS"
GOOGLE_CLIENT_ID: Final[str] = "GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET: Final[str] = "GOOGLE_CLIENT_SECRET"
BOX_CLIENT_ID: Final[str] = "BOX_CLIENT_ID"
BOX_CLIENT_SECRET: Final[str] = "BOX_CLIENT_SECRET"
MICROSOFT_CLIENT_ID: Final[str] = "MICROSOFT_CLIENT_ID"
MICROSOFT_CLIENT_SECRET: Final[str] = "MICROSOFT_CLIENT_SECRET"

google_client_id = os.environ.get(GOOGLE_CLIENT_ID)
google_client_secret = os.environ.get(GOOGLE_CLIENT_SECRET)
box_client_id = os.environ.get(BOX_CLIENT_ID)
box_client_secret = os.environ.get(BOX_CLIENT_SECRET)
microsoft_client_id = os.environ.get(MICROSOFT_CLIENT_ID)
microsoft_client_secret = os.environ.get(MICROSOFT_CLIENT_SECRET)

app_runtime_parameters = []

# DataRobot OAuth Providers Service
provider_ids: list[pulumi.Output[str]] = []

if google_client_id and google_client_secret:
    pulumi.info(
        "Google OAuth credentials found, adding to application runtime parameters."
    )
    pulumi.export("Google Client ID", google_client_id)

    google_oauth = datarobot.AppOauth(
        f"[{PROJECT_NAME}] Agent Application Google Client",
        type="google",
        client_id=google_client_id,
        client_secret=google_client_secret,
    )
    pulumi.export("Google OAuth Provider ID", google_oauth.id)
    provider_ids.append(google_oauth.id)

if box_client_id and box_client_secret:
    pulumi.info("Box credentials found, adding to application runtime parameters.")
    pulumi.export("Box Client ID", box_client_id)

    box_oauth = datarobot.AppOauth(
        f"[{PROJECT_NAME}] Agent Application Box Client",
        type="box",
        client_id=box_client_id,
        client_secret=box_client_secret,
    )

    pulumi.export("Box OAuth Provider ID", box_oauth.id)
    provider_ids.append(box_oauth.id)

if microsoft_client_id and microsoft_client_secret:
    pulumi.info(
        "Microsoft OAuth credentials found, adding to application runtime parameters."
    )
    pulumi.export("Microsoft Client ID", microsoft_client_id)

    microsoft_oauth = datarobot.AppOauth(
        f"[{PROJECT_NAME}] Agent Application Microsoft Client",
        type="microsoft",
        client_id=microsoft_client_id,
        client_secret=microsoft_client_secret,
    )
    pulumi.export("Microsoft OAuth Provider ID", microsoft_oauth.id)
    provider_ids.append(microsoft_oauth.id)

oauth_providers_output: pulumi.Output[str] = pulumi.Output.all(*provider_ids).apply(
    lambda ids: json.dumps(ids)
)

app_runtime_parameters += [
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        type="string",
        key=DATAROBOT_OAUTH_PROVIDERS,
        value=oauth_providers_output,
    )
]
export("DATAROBOT_OAUTH_PROVIDERS", oauth_providers_output)
