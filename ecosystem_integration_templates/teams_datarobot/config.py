#!/usr/bin/env python3
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os


class DefaultConfig:
    """Bot Configuration"""

    PORT = os.environ.get("PORT", 443)  # Port to run the bot service on
    SERVER = os.environ.get("SERVER", "0.0.0.0")  # Server IP. Accepts localhost
    APP_ID = os.environ.get(
        "MicrosoftAppId", ""
    )  # Bot Identifier from https://dev.teams.microsoft.com/bots/<<IDENTIFIER>>/configure
    APP_PASSWORD = os.environ.get(
        "MicrosoftAppPassword", ""
    )  # Client Secret from Bot Configure page.
    DATAROBOT_TOKEN = os.environ.get("apiToken", "")  # DataRobot API Token for authorization
    DATAROBOT_ENDPOINT = os.environ.get(
        "DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2"
    )  # DataRobot Endpoint
    DATAROBOT_DEPLOYMENT = os.environ.get(
        "deploymentId", "65cd8cb6481e3be33dcd194c"
    )  # DataRobot LLM Deployment Identifier
