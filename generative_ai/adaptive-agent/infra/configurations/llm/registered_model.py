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
This LLM configuration option is useful when you already have an LLM Deployed.
It will pull it into the playground and use case. It isn't sufficient if you
have a registered model you would like added to an LLM Blueprint and deployed.
For that, you'll need to choose the "registered_model_llm.py" option
"""

import os
import datarobot as dr
from datarobot_pulumi_utils.pulumi import export
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments
import pulumi
import pulumi_datarobot as datarobot

from . import use_case
from .libllm import (
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

TEXTGEN_REGISTERED_MODEL_ID = os.environ["TEXTGEN_REGISTERED_MODEL_ID"]

llm_application_name: str = "llm"
llm_resource_name: str = "[llm]"
default_model: str = os.environ.get(
    "LLM_DEFAULT_MODEL", "datarobot/datarobot-deployed-llm"
)

# Verify the feature flags are available
validate_feature_flags(REQUIRED_FEATURE_FLAGS)

playground = datarobot.Playground(
    use_case_id=use_case.id,
    resource_name=f"LLM Playground [{PROJECT_NAME}]" + llm_resource_name,
)

# Pull in the registered model
proxy_llm_registered_model = datarobot.RegisteredModel.get(
    resource_name="Existing TextGen Registered Model",
    id=TEXTGEN_REGISTERED_MODEL_ID,
)

prediction_environment = datarobot.PredictionEnvironment(
    resource_name="LLM Prediction Environment " + llm_resource_name,
    platform=dr.enums.PredictionEnvironmentPlatform.DATAROBOT_SERVERLESS,
)

# Create the deployment for the passed in registered model
proxy_llm_deployment = datarobot.Deployment(
    resource_name=f"LLM Deployment [{PROJECT_NAME}]",
    registered_model_version_id=proxy_llm_registered_model.version_id,
    prediction_environment_id=prediction_environment.id,
    label=f"Data Analyst LLM Deployment [{PROJECT_NAME}]",
    use_case_ids=[use_case.id],
    opts=pulumi.ResourceOptions(replace_on_changes=["registered_model_version_id"]),
)

# Use Pulumi apply to verify the registered model LLM once deployed
proxy_llm_deployment.id.apply(  # type: ignore[missing-argument]
    lambda id: verify_llm(model_id=f"{default_model}", deployment_id=id)  # type: ignore[invalid-argument-type]
)

# Make a LLM Blueprint from the deployed registered model
proxy_llm_validation = datarobot.CustomModelLlmValidation(
    resource_name="LLM Blueprint Validation " + llm_resource_name,
    chat_model_id=default_model.removeprefix("datarobot/"),
    deployment_id=proxy_llm_deployment.id,
    use_case_id=use_case.id,
)
llm_blueprint = datarobot.LlmBlueprint(
    resource_name="LLM Blueprint " + llm_resource_name,
    custom_model_llm_settings=datarobot.LlmBlueprintCustomModelLlmSettingsArgs(
        validation_id=proxy_llm_validation.id,
    ),
    llm_id="custom-model",
    playground_id=playground.id,
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
    runtime_parameter_values=[],
)

# Register the custom model from the LLM Blueprint
llm_blueprint_registered_model = datarobot.RegisteredModel(
    resource_name="LLM Registered Model " + llm_resource_name,
    custom_model_version_id=llm_custom_model.version_id,
    name="LLM Registered Model " + llm_resource_name,
    use_case_ids=[use_case.id],
)

# Deploy the LLM Blueprint Registered Model
llm_deployment = datarobot.Deployment(
    resource_name="LLM Blueprint Deployment " + llm_resource_name,
    registered_model_version_id=llm_blueprint_registered_model.version_id,
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
        value=default_model,
    ),
    datarobot.ApplicationSourceRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL_FRIENDLY_NAME",
        type="string",
        value=proxy_llm_registered_model.name,
    ),
]
custom_model_runtime_parameters = [
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEPLOYMENT_ID",
        type="string",
        value=proxy_llm_deployment.id,
    ),
    datarobot.CustomModelRuntimeParameterValueArgs(
        key="LLM_DEFAULT_MODEL",
        type="string",
        value=default_model,
    ),
]

pulumi.export("Deployment ID " + llm_resource_name, proxy_llm_deployment.id)
export("LLM_DEPLOYMENT_ID", proxy_llm_deployment.id)
export("LLM_DEFAULT_MODEL", default_model)
export("LLM_DEFAULT_MODEL_FRIENDLY_NAME", proxy_llm_registered_model.name)
