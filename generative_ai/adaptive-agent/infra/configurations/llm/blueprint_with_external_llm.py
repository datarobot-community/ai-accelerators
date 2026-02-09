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
This configuration option is right choice when you already have an LLM from Azure, Bedrock,
Anthropic, Vertex, etc. This way you can monitor and scale your LLM directly with the added
benefits of the DataRobot platform such as governance, guard models, controlled API access,
and monitoring.
"""

import datarobot as dr
import os
import pulumi
import pulumi_datarobot as datarobot
from datarobot_pulumi_utils.pulumi import export
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments

from . import use_case
from .libllm import (
    get_runtime_values,
    validate_feature_flags,
    verify_llm,
)

__all__ = [
    "custom_model_runtime_parameters",
    "app_runtime_parameters",
    "default_model",
    "llm_application_name",
    "llm_resource_name",
]

REQUIRED_FEATURE_FLAGS = {
    "ENABLE_MLOPS": True,
    "ENABLE_CUSTOM_INFERENCE_MODEL": True,
    "ENABLE_PUBLIC_NETWORK_ACCESS_FOR_ALL_CUSTOM_MODELS": True,
    "ENABLE_MLOPS_TEXT_GENERATION_TARGET_TYPE": True,
}

__all__ = [
    "llm_application_name",
    "llm_resource_name",
]

llm_application_name: str = "llm"
llm_resource_name: str = "[llm]"
default_model: str = os.environ.get(
    "LLM_DEFAULT_MODEL", "datarobot/azure/gpt-5-mini-2025-08-07"
)
default_llm_id: str = os.environ.get(
    "LLM_DEFAULT_LLM_ID",
    "azure-openai-gpt-5-mini",  # External LLM ID from the Playground
)
default_llm_friendly_name: str = os.environ.get(
    "LLM_DEFAULT_LLM_NAME",
    "Azure OpenAI GPT-5 Mini",  # Shown in the Web UI
)

validate_feature_flags(REQUIRED_FEATURE_FLAGS)
llm_credential_runtime_params = get_runtime_values(default_llm_id)
# This will ensure your credentials are working properly
# https://docs.litellm.ai/docs/providers for more details
# on what string to pass to `verify_llm` This default
# example is assuming Azure OpenAI with a OPENAI_API_DEPLOYMENT_ID='azure-openai-gpt-5-mini'.
# You combine that with azure/gpt-5-mini-2025-08-07 for LiteLLM to verify the model.
# Similar instructions exist for Bedrock: https://docs.litellm.ai/docs/providers/bedrock
# and Vertex: https://docs.litellm.ai/docs/providers/vertex
verify_llm(f"azure/{os.getenv('OPENAI_API_DEPLOYMENT_ID')}")

playground = datarobot.Playground(
    use_case_id=use_case.id,
    resource_name="LLM Playground " + llm_resource_name,
)

llm_blueprint = datarobot.LlmBlueprint(
    resource_name="LLM Blueprint " + llm_resource_name,
    playground_id=playground.id,
    llm_id=default_llm_id,
    llm_settings=datarobot.LlmBlueprintLlmSettingsArgs(
        max_completion_length=2048,
        temperature=0.1,
        top_p=None,
    ),
)

llm_custom_model = datarobot.CustomModel(
    resource_name="LLM Custom Model " + llm_resource_name,
    name="LLM Custom Model " + llm_resource_name,
    target_name="resultText",
    target_type=dr.enums.TARGET_TYPE.TEXT_GENERATION,
    replicas=1,
    base_environment_id=RuntimeEnvironments.PYTHON_312_MODERATIONS.value.id,
    use_case_ids=[use_case.id],
    source_llm_blueprint_id=llm_blueprint.id,
    runtime_parameter_values=llm_credential_runtime_params,
)

prediction_environment = datarobot.PredictionEnvironment(
    resource_name="LLM Prediction Environment " + llm_resource_name,
    platform=dr.enums.PredictionEnvironmentPlatform.DATAROBOT_SERVERLESS,
)

# Register the custom model
llm_registered_model = datarobot.RegisteredModel(
    resource_name="LLM Registered Model " + llm_resource_name,
    custom_model_version_id=llm_custom_model.version_id,
    name="LLM Registered Model " + llm_resource_name,
    use_case_ids=[use_case.id],
)

# Deploy the registered model
llm_deployment = datarobot.Deployment(
    resource_name="LLM Blueprint Deployment " + llm_resource_name,
    registered_model_version_id=llm_registered_model.version_id,
    prediction_environment_id=prediction_environment.id,
    label=f"LLM Deployment [{PROJECT_NAME}] " + llm_resource_name,
    use_case_ids=[use_case.id],
    association_id_settings=datarobot.DeploymentAssociationIdSettingsArgs(
        column_names=["association_id"],
        auto_generate_id=False,
        required_in_prediction_requests=True,
    ),
    predictions_data_collection_settings=datarobot.DeploymentPredictionsDataCollectionSettingsArgs(
        enabled=True,
    ),
    predictions_settings=datarobot.DeploymentPredictionsSettingsArgs(
        min_computes=0, max_computes=2
    ),
    opts=pulumi.ResourceOptions(replace_on_changes=["registered_model_version_id"]),
)

app_runtime_parameters = [
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="LLM_DEPLOYMENT_ID",
        type="string",
        value=llm_deployment.id,
    ),
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_llm_id,
    ),
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL_FRIENDLY_NAME",
        type="string",
        value=default_llm_friendly_name,
    ),
]
custom_model_runtime_parameters = [
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEPLOYMENT_ID",
        type="string",
        value=llm_deployment.id,
    ),
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_llm_id,
    ),
]
pulumi.export("Deployment ID " + llm_resource_name, llm_deployment.id)
export("LLM_DEPLOYMENT_ID", llm_deployment.id)
export("LLM_DEFAULT_MODEL", default_llm_id)
export("LLM_DEFAULT_MODEL_FRIENDLY_NAME", default_llm_friendly_name)
