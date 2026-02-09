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
# ------------------------------------------------------------------------------
"""
All configuration for the agent application. The config class handles
loading variables from environment, .env files, Pulumi outputs, and
DataRobot credentials automatically.
"""

from typing import Any

from datarobot.core.config import DataRobotAppFrameworkBaseSettings
from pydantic import Field, model_validator


class Config(DataRobotAppFrameworkBaseSettings):
    """
    This class finds variables in the priority order of: env
    variables (including Runtime Parameters), .env, file_secrets, then
    Pulumi output variables.
    """

    llm_deployment_id: str | None = None
    llm_default_model: str = "datarobot/azure/gpt-5-mini-2025-08-07"
    use_datarobot_llm_gateway: bool = False
    mcp_deployment_id: str | None = None
    external_mcp_url: str | None = None

    # Adaptive Agent Demo settings
    main_model: str = Field(
        default="datarobot/azure/gpt-4o",
        description="Main model for agent responses (used when thinking mode is active)"
    )
    fast_model: str = Field(
        default="datarobot/azure/gpt-4o-mini",
        description="Faster model for simple responses (used when thinking mode is off)"
    )
    reflection_model: str = Field(
        default="datarobot/azure/gpt-4o-mini",
        description="Model for reflection/correction detection"
    )
    enable_adaptive_thinking: bool = Field(
        default=True,
        description="Enable adaptive think mode toggling based on conversation analysis"
    )

    local_dev_port: int = Field(
        default=8842, validation_alias="AGENT_PORT", ge=1, le=65535
    )

    @model_validator(mode="before")
    @classmethod
    def replace_placeholder_values(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for field_name, field_info in cls.model_fields.items():
                if data.get(field_name) == "SET_VIA_PULUMI_OR_MANUALLY":
                    data[field_name] = field_info.default
        return data
