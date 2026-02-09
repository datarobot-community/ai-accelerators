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
This configuration option is available as the most flexible option with the most
production controls. It uses our LLM Blueprint and LLM Gateway options to enable
multiple LLMs through a single deployment with all of the DataRobot governance
and monitoring baked in.
"""

import os
import datarobot as dr
import pulumi
import pulumi_datarobot as datarobot

from datarobot_pulumi_utils.pulumi import export
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments

from . import use_case
from .libllm import (
    validate_feature_flags,
    verify_llm,
    verify_llm_gateway_model_availability,
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

llm_application_name: str = "llm"
llm_resource_name: str = "[llm]"
# This is the model_id that the DataRobot LLM Gateway expects.
# You can get a list of these models by running:
"""
import datarobot
dr_client = datarobot.Client()
response = dr_client.get("genai/llmgw/catalog/")
data = response.json()
print("\n.   - ".join(
    [
        f"{model['model']}:{model['llmId']}"
        for model in data["data"]
        if model["isActive"]
    ]
))
"""
default_model: str = os.environ.get(
    "LLM_DEFAULT_MODEL", "datarobot/azure/gpt-5-mini-2025-08-07"
)
default_llm_id: str = os.environ.get(
    "LLM_DEFAULT_LLM_ID",
    "azure-openai-gpt-5-mini",  # External LLM ID from the Playground
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
        key="LLM_DEPLOYMENT_ID",
        type="string",
        value=llm_deployment.id,
    ),
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_model,
    ),
]
pulumi.export("Deployment ID " + llm_resource_name, llm_deployment.id)
export("LLM_DEPLOYMENT_ID", llm_deployment.id)
export("USE_DATAROBOT_LLM_GATEWAY", "1")
export("LLM_DEFAULT_MODEL", default_model)
