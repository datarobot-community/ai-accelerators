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
Utility functions for creating needed runtime parameters, credentials, and validating
the LLM configuration is functional prior to deployment.
"""

from dataclasses import dataclass, field
import os
import tempfile
from collections import namedtuple
from pathlib import Path
import logging

import datarobot
import pulumi
import pulumi_datarobot
from litellm import completion


from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.common.feature_flags import (
    eval_feature_flag_statuses,
    FeatureFlagSet,
)

INFRA_DIR = Path(__file__).parent

log = logging.getLogger(__name__)


# LLM Credential Management Mapping
RuntimeParameterValueArgs = namedtuple(
    "RuntimeParameterValueArgs", ["key", "type", "default"], defaults=[None]
)


@dataclass
class ProviderCredential:
    # The provider: azure, bedrock, etc.
    provider: str
    # The environment variables for the credentials needed by the provider.
    # If a tuple, we'll look for one and map it to the others if they are not set
    env_vars: list[str] = field(default_factory=list)
    # The possible prefixes that both DataRobot Pulumi need and LiteLLM Needs
    prefix_list: list[str] = field(default_factory=list)
    runtime_parameters: list[RuntimeParameterValueArgs] = field(default_factory=list)

    def __post_init__(self):
        """
        Do the env_vars search and prefix list mapping straight into os.environ. i.e, OPENAI_API_KEY to AZURE_API_KEY
        """
        for var_name in self.env_vars:
            # Find the first existing variable across all prefixes
            found_value = None
            for prefix in self.prefix_list:
                full_var_name = f"{prefix}{var_name}"
                if full_var_name in os.environ:
                    found_value = os.environ[full_var_name]
                    break
            if not found_value:
                continue

            # Special handling for Google credentials
            if var_name == "_APPLICATION_CREDENTIALS":
                # GOOGLE_APPLICATION_CREDENTIALS is a file path, need to read and set GOOGLE_SERVICE_ACCOUNT as JSON string
                try:
                    with open(found_value, "r") as f:
                        json_content = f.read()
                    if "GOOGLE_SERVICE_ACCOUNT" not in os.environ:
                        os.environ["GOOGLE_SERVICE_ACCOUNT"] = json_content
                except (FileNotFoundError, IOError):
                    pass  # If file doesn't exist, skip cross-population
                continue

            if var_name == "_SERVICE_ACCOUNT":
                # GOOGLE_SERVICE_ACCOUNT is a JSON string, need to create file and set GOOGLE_APPLICATION_CREDENTIALS
                try:
                    temp_file = tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    )
                    temp_file.write(found_value)
                    temp_file.close()
                    if "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file.name
                except Exception:
                    pass  # If file creation fails, skip cross-population
                continue

            # Copy the found value to all missing combinations
            for prefix in self.prefix_list:
                full_var_name = f"{prefix}{var_name}"
                if full_var_name not in os.environ:
                    os.environ[full_var_name] = found_value

    @property
    def runtime_parameter_values(
        self,
    ) -> list[pulumi_datarobot.CustomModelRuntimeParameterValueArgs]:
        """Return the pulumi runtime parameters required for the external model"""
        runtime_values: list[pulumi_datarobot.CustomModelRuntimeParameterValueArgs] = []
        credential: (
            pulumi_datarobot.ApiTokenCredential
            | pulumi_datarobot.GoogleCloudCredential
            | pulumi_datarobot.AwsCredential
        )
        for param in self.runtime_parameters:
            if param.type == "string":
                runtime_values.append(
                    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
                        key=param.key,
                        type=param.type,
                        value=os.environ.get(param.key) or param.default,
                    )
                )
            elif param.type == "credential":
                credential = pulumi_datarobot.ApiTokenCredential(
                    resource_name=f"{pulumi.get_project()} {param.key} Credential [{PROJECT_NAME}]",
                    api_token=os.environ.get(param.key),
                )
                runtime_values.append(
                    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
                        key=param.key, type="credential", value=credential.id
                    )
                )
            elif param.type == "google_credential":
                credential = pulumi_datarobot.GoogleCloudCredential(
                    resource_name=f"{pulumi.get_project()} {param.key} Credential [{PROJECT_NAME}]",
                    gcp_key=os.environ.get(param.key),
                )
                runtime_values.append(
                    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
                        key=param.key,
                        type="credential",
                        value=credential.id,
                    )
                )
            elif param.type == "aws_credential":
                credential = pulumi_datarobot.AwsCredential(
                    resource_name=f"{pulumi.get_project()} {param.key} Credential [{PROJECT_NAME}]",
                    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
                    aws_session_token=os.environ.get("AWS_SESSION_TOKEN"),
                )
                runtime_values.append(
                    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
                        key=param.key,
                        type="credential",
                        value=credential.id,
                    )
                )
        return runtime_values


PROVIDER_CREDENTIALS_MAP = {
    # The "Big Three" Cloud Providers
    "azure": ProviderCredential(
        provider="azure",
        env_vars=["_API_KEY", "_API_BASE", "_API_VERSION", "_API_DEPLOYMENT_ID"],
        prefix_list=["OPENAI", "AZURE"],
        runtime_parameters=[
            RuntimeParameterValueArgs(key="OPENAI_API_KEY", type="credential"),
            RuntimeParameterValueArgs(key="OPENAI_API_BASE", type="string"),
            RuntimeParameterValueArgs(key="OPENAI_API_VERSION", type="string"),
            RuntimeParameterValueArgs(key="OPENAI_API_DEPLOYMENT_ID", type="string"),
        ],
    ),
    "bedrock": ProviderCredential(
        provider="bedrock",
        env_vars=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME"],
        runtime_parameters=[
            RuntimeParameterValueArgs(key="AWS_ACCOUNT", type="aws_credential"),
            RuntimeParameterValueArgs(
                key="AWS_REGION_NAME", type="string", default="us-east-1"
            ),
        ],
    ),
    "vertex_ai": ProviderCredential(
        provider="vertex_ai",
        env_vars=["_APPLICATION_CREDENTIALS", "_SERVICE_ACCOUNT"],
        prefix_list=["VERTEXAI", "GOOGLE"],
        runtime_parameters=[
            RuntimeParameterValueArgs(
                key="GOOGLE_SERVICE_ACCOUNT", type="google_credential"
            ),
            RuntimeParameterValueArgs(
                key="GOOGLE_REGION", type="string", default="us-west1"
            ),
        ],
    ),
    "anthropic": ProviderCredential(
        provider="anthropic",
        env_vars=["ANTHROPIC_API_KEY"],
        runtime_parameters=[
            RuntimeParameterValueArgs(key="ANTHROPIC_API_KEY", type="credential"),
        ],
    ),
    "cohere": ProviderCredential(
        provider="cohere",
        env_vars=["COHERE_API_KEY"],
        runtime_parameters=[
            RuntimeParameterValueArgs(key="COHERE_API_KEY", type="credential"),
        ],
    ),
    "togetherai": ProviderCredential(
        provider="togetherai",
        env_vars=["TOGETHERAI_API_KEY"],
        runtime_parameters=[
            RuntimeParameterValueArgs(key="TOGETHERAI_API_KEY", type="credential"),
        ],
    ),
}


def get_runtime_values(
    model_id: str,
) -> list[pulumi_datarobot.CustomModelRuntimeParameterValueArgs]:
    """Get the runtime values for the active LLM module."""
    # Extract provider from model_id - try slash first (new format), then dash (legacy format)
    if "/" in model_id:
        provider = model_id.split("/")[0]
    elif "-" in model_id:
        provider = model_id.split("-")[0]
    else:
        provider = model_id
    # Map common aliases to their canonical provider names
    provider_aliases = {"amazon": "bedrock", "google": "vertex_ai"}
    provider = provider_aliases.get(provider, provider)
    credential = PROVIDER_CREDENTIALS_MAP[provider]
    return credential.runtime_parameter_values


def validate_feature_flags(flags: FeatureFlagSet) -> None:
    corrections, invalid_flags = eval_feature_flag_statuses(flags)
    for flag in invalid_flags:
        correct_value = flags[flag]
        pulumi.warn(
            f"Feature flag '{flag}' is required to be {correct_value} but is no longer a valid DataRobot feature flag."
        )
    for flag, correct_value in corrections:
        pulumi.error(
            f"This app template requires that feature flag '{flag}' is set "
            f"to {correct_value}. Contact your DataRobot representative for "
            "assistance."
        )
    if corrections:
        raise pulumi.RunError("Please correct feature flag settings and run again.")


def verify_llm_gateway_model_availability(model_id: str) -> None:
    """
    Validate the model is in the catalog
    """
    model_id = model_id.removeprefix("datarobot/")
    dr_client = datarobot.Client()
    response = dr_client.get("genai/llmgw/catalog/")
    data = response.json()
    active_models_display = "\n.   - ".join(
        [model["model"] for model in data["data"] if model["isActive"]]
    )
    matched_models = [
        model
        for model in data["data"]
        if (model["model"] == model_id or model["llmId"] == model_id)
    ]
    if not matched_models:
        err_message = f"""
        Model '{model_id}' not found in catalog. Model availability may vary depending on
        region and organization settings.
        
        To change the default_model, set the environment variable
        'LLM_DEFAULT_MODEL' to an active model or edit the default_model directly
        in the infra/infra/libllm.py.jinja file.

        If you have multiple Pulumi LLM configurations, please set the appropriate environment
        variable or update the respective infra/infra/* file for the configuration you want to modify.

        Available models: {active_models_display}
        """
        raise ValueError(err_message)
    if len(matched_models) != 1:
        raise ValueError(
            f"Multiple models found for '{model_id}' in catalog. {matched_models}"
        )
    if matched_models[0]["isDeprecated"] and matched_models[0]["isActive"]:
        log.warning(
            """Model '%s' is deprecated but active. The end of support date falls within 90 days.
            It is recommended that you choose a different model, where possible.
            
            Available models: %s""",
            model_id,
            active_models_display,
        )
    if not matched_models[0]["isActive"]:
        raise ValueError(
            f"Model '{model_id}' is not active or is retired. Available models: {active_models_display}"
        )


def verify_llm(model_id: str | None = None, deployment_id: str | None = None) -> None:
    """
    Verify that the specified LLM is valid, available, and you can say hello
    """

    # Pre-existing deployment
    if deployment_id:
        dr_client = datarobot.Client()
        deployment_chat_base_url = f"{dr_client.endpoint.rstrip('/')}/deployments/{deployment_id}/chat/completions"
        response = completion(
            model=model_id or "datarobot/datarobot-deployed-llm",
            messages=[{"content": "Hi", "role": "user"}],
            api_base=deployment_chat_base_url,
        )
        assert len(response["choices"][0]["message"]["content"]) > 0
        return

    if model_id is None:
        raise ValueError("model_id must be provided to verify_llm")

    # Map legacy to LiteLLM
    if "-" in model_id:
        provider_aliases = {
            "azure": "azure",
            "amazon": "bedrock",
            "google": "vertex_ai",
        }
        provider = model_id.split("-")[0]
        if provider in provider_aliases:
            provider = provider_aliases[provider]
            model_id = provider + "/" + "-".join(model_id.split("-")[1:])
    # Map common aliases to their canonical provider names
    provider = provider_aliases.get(provider, provider)
    response = completion(
        model=model_id,
        messages=[{"content": "Hi", "role": "user"}],
    )
    assert len(response["choices"][0]["message"]["content"]) > 0
