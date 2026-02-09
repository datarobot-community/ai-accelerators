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
"""
Choose this option for direct DataRobot LLM Gateway integration.
"""

import os
from datarobot_pulumi_utils.pulumi import export
import pulumi_datarobot as datarobot

from .libllm import (
    validate_feature_flags,
    verify_llm,
    verify_llm_gateway_model_availability,
)

__all__ = [
    "app_runtime_parameters",
    "custom_model_runtime_parameters",
    "default_model",
    "llm_application_name",
]

REQUIRED_FEATURE_FLAGS = {
    "ENABLE_MLOPS": True,
    "ENABLE_CUSTOM_INFERENCE_MODEL": True,
    "ENABLE_PUBLIC_NETWORK_ACCESS_FOR_ALL_CUSTOM_MODELS": True,
    "ENABLE_MLOPS_TEXT_GENERATION_TARGET_TYPE": True,
    "ENABLE_MLOPS_RESOURCE_REQUEST_BUNDLES": True,
}

llm_application_name: str = "llm"

# This is the model_id that the DataRobot LLM Gateway expects.
# You can get a list of these models by running:
"""
import datarobot
dr_client = datarobot.Client()
response = dr_client.get("genai/llmgw/catalog/")
data = response.json()
print("\n.   - ".join(
    [
        model["model"]
        for model in data["data"]
        if model["isActive"]
    ]
))
"""
default_model: str = os.environ.get(
    "LLM_DEFAULT_MODEL", "datarobot/azure/gpt-5-mini-2025-08-07"
)

# Verify everything is configured properly for this configuration option.
validate_feature_flags(REQUIRED_FEATURE_FLAGS)

# This does a quick check that validates the selected model is available
# by checking the LLM Gateway. If it isn't, it will raise an error
# with the list of models that are available and active.
verify_llm_gateway_model_availability(default_model)

# LiteLLM support DataRobot as a provider, so this validates
# everything is working and the default LLM you've chosen is available
verify_llm(f"{default_model}")

app_runtime_parameters = [
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="USE_DATAROBOT_LLM_GATEWAY",
        type="string",
        value="1",
    ),
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_model,
    ),
]
custom_model_runtime_parameters = [
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="USE_DATAROBOT_LLM_GATEWAY",
        type="string",
        value="1",
    ),
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_model,
    ),
]
export("USE_DATAROBOT_LLM_GATEWAY", "1")
export("LLM_DEFAULT_MODEL", default_model)
