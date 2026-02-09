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
import re
import textwrap
from typing import Sequence, Final

import pulumi
import pulumi_datarobot
import datarobot as dr
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments

from . import project_dir, use_case

from .mcp_server_user_params import MCP_USER_RUNTIME_PARAMETERS

DEFAULT_EXECUTION_ENVIRONMENT = "Python 3.11 GenAI Agents"

EXCLUDE_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        # Test and development files
        r".*tests/.*",
        r".*\.coverage",
        r".*coverage\.xml",
        r".*coveragerc",
        r".*htmlcov/.*",
        r".*env",
        r".pre-commit-config.yaml",
        # Cache and temporary files
        r".*\.DS_Store",
        r".*\.pyc",
        r".*\.pyo",
        r".*\.pyd",
        r".*\.ruff_cache/.*",
        r".*\.venv/.*",
        r".*\.mypy_cache/.*",
        r".*__pycache__/.*",
        r".*\.pytest_cache/.*",
        r".*\.tox/.*",
        r".*\.nox/.*",
        r".*\.uv/.*",
        # Documentation and examples
        r".*docs/.*",
        r".*examples/.*",
        r".*samples/.*",
        r".*\.md$",
        r".*\.rst$",
        r".*\.txt$",
        # IDE and editor files
        r".*\.vscode/.*",
        r".*\.idea/.*",
        r".*\.sublime-.*",
        r".*\.vim/.*",
        # OS specific files
        r".*Thumbs\.db",
        r".*desktop\.ini",
        r".*\.swp",
        r".*\.swo",
        r".*~$",
        # Build artifacts
        r".*build/.*",
        r".*dist/.*",
        r".*egg-info/.*",
        r".*\.egg/.*",
        # Logs
        r".*\.log$",
        r".*logs/.*",
    ]
]


__all__ = [
    "execution_environment",
    "deployment",
    "mcp_server_mcp_endpoint",
    "mcp_server_base_endpoint",
    "mcp_custom_model_runtime_parameters",
]

mcp_server_asset_name: str = f"[{PROJECT_NAME}] [mcp_server]"

deployments_application_path = project_dir.parent / "mcp_server"


def _prep_metadata_yaml(
    runtime_parameter_values: Sequence[
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs
    ],
) -> None:
    from jinja2 import BaseLoader, Environment

    runtime_parameter_specs = "\n".join(
        [
            textwrap.dedent(
                f"""\
            - fieldName: {param.key}
              type: {param.type}
        """
            )
            for param in runtime_parameter_values
        ]
    )
    if not runtime_parameter_specs:
        runtime_parameter_specs = "    []"

    # Read both templates
    with open(deployments_application_path / "metadata.yaml") as f:
        base_template_content = f.read()

    recipe_template_path = deployments_application_path / "user-metadata.yaml"
    recipe_template_content = ""
    if recipe_template_path.exists():
        with open(recipe_template_path) as rf:
            recipe_template_content = rf.read()

    # Combine template contents
    combined_template = base_template_content
    if recipe_template_content:
        # Assuming both templates have a runtimeParameterDefinitions section
        # Remove the header from recipe template and append its content
        recipe_lines = recipe_template_content.split("\n")
        for i, line in enumerate(recipe_lines):
            if line.strip() == "runtimeParameterDefinitions:":
                recipe_content = "\n".join(recipe_lines[i + 1 :])
                combined_template = combined_template.rstrip() + "\n" + recipe_content

    # Render the combined template
    template = Environment(loader=BaseLoader()).from_string(combined_template)
    (deployments_application_path / "model-metadata.yaml").write_text(
        template.render(
            additional_params=runtime_parameter_specs,
        )
    )


def get_deployments_app_files(
    runtime_parameter_values: Sequence[
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs,
    ],
) -> list[tuple[str, str]]:
    _prep_metadata_yaml(runtime_parameter_values)

    # Essential files only - whitelist approach to stay under 100 file limit
    essential_files = [
        "app/",
        "model-metadata.yaml",
        "pyproject.toml",
        "uv.lock",
    ]
    source_files = []
    # Add essential files
    for essential_file in essential_files:
        file_path = deployments_application_path / essential_file
        if file_path.exists():
            if file_path.is_file():
                source_files.append((str(file_path), essential_file))
            elif file_path.is_dir():
                # Add all Python files from app directory only
                for py_file in file_path.rglob("*.py"):
                    if py_file.is_file():
                        rel_path = py_file.relative_to(deployments_application_path)
                        source_files.append((str(py_file), str(rel_path)))

    # Filter out any files that match exclude patterns (safety check)
    source_files = [
        (file_path, file_name)
        for file_path, file_name in source_files
        if not any(
            exclude_pattern.match(file_name) for exclude_pattern in EXCLUDE_PATTERNS
        )
    ]

    # Remove duplicates based on file_name (relative path)
    seen_files = set()
    unique_source_files = []
    for file_path_, file_name in source_files:
        if file_name not in seen_files:
            seen_files.add(file_name)
            unique_source_files.append((file_path_, file_name))
    return unique_source_files


# Start of Pulumi settings and application infrastructure
if len(os.environ.get("DATAROBOT_DEFAULT_MCP_EXECUTION_ENVIRONMENT", "")) > 0:
    # Get the default execution environment from environment variable
    execution_environment_id = os.environ["DATAROBOT_DEFAULT_MCP_EXECUTION_ENVIRONMENT"]
    if DEFAULT_EXECUTION_ENVIRONMENT in execution_environment_id:
        pulumi.info("Using default GenAI Agentic Execution Environment.")
        execution_environment_id = RuntimeEnvironments.PYTHON_311_GENAI_AGENTS.value.id

    # Get the pinned version ID if provided
    execution_environment_version_id = os.environ.get(
        "DATAROBOT_DEFAULT_MCP_EXECUTION_ENVIRONMENT_VERSION_ID", None
    )
    if not re.match("^[a-f\d]{24}$", str(execution_environment_version_id)):
        pulumi.info(
            "No valid execution environment version ID provided, using latest version."
        )
        execution_environment_version_id = None

    pulumi.info(
        "Using existing execution environment: "
        + execution_environment_id
        + " Version ID: "
        + str(execution_environment_version_id)
    )

    execution_environment = pulumi_datarobot.ExecutionEnvironment.get(
        id=execution_environment_id,
        version_id=execution_environment_version_id,
        resource_name=mcp_server_asset_name + " Execution Environment",
    )
else:
    pulumi.info("Using docker folder to compile the execution environment")
    execution_environment = pulumi_datarobot.ExecutionEnvironment(
        resource_name=mcp_server_asset_name + " Execution Environment",
        name=mcp_server_asset_name,
        description="Execution environment for MCP server",
        programming_language="python",
        use_cases=["customModel"],
        docker_context_path=str(project_dir.parent / "mcp_server" / "docker"),
        opts=pulumi.ResourceOptions(retain_on_delete=False),
    )

# Custom Model
deployments_model_runtime_parameters: list[
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs
] = [
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="mcp_server_name",
        type="string",
        value=os.getenv("MCP_SERVER_NAME", "datarobot-mcp-server"),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="mcp_server_log_level",
        type="string",
        value=os.getenv("MCP_SERVER_LOG_LEVEL", "WARNING"),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="mcp_server_register_dynamic_tools_on_startup",
        type="boolean",
        value=str(
            os.getenv("MCP_SERVER_REGISTER_DYNAMIC_TOOLS_ON_STARTUP", "false")
        ).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="tool_registration_duplicate_behavior",
        type="string",
        value=str(
            os.getenv("MCP_SERVER_TOOL_REGISTRATION_DUPLICATE_BEHAVIOR", "warn")
        ).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="tool_registration_allow_empty_schema",
        type="boolean",
        value=str(
            os.getenv("MCP_SERVER_TOOL_REGISTRATION_ALLOW_EMPTY_SCHEMA", "false")
        ).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="mcp_server_register_dynamic_prompts_on_startup",
        type="boolean",
        value=str(
            os.getenv("MCP_SERVER_REGISTER_DYNAMIC_PROMPTS_ON_STARTUP", "false")
        ).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="prompt_registration_duplicate_behavior",
        type="string",
        value=str(
            os.getenv("MCP_SERVER_PROMPT_REGISTRATION_DUPLICATE_BEHAVIOR", "warn")
        ).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="app_log_level", type="string", value=os.getenv("APP_LOG_LEVEL", "INFO")
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="otel_attributes", type="string", value=os.getenv("OTEL_ATTRIBUTES", "{}")
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="otel_enabled",
        type="boolean",
        value=str(os.getenv("OTEL_ENABLED", "true")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="otel_enabled_http_instrumentors",
        type="boolean",
        value=str(os.getenv("OTEL_ENABLED_HTTP_INSTRUMENTORS", "false")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_memory_management",
        type="boolean",
        value=str(os.getenv("ENABLE_MEMORY_MANAGEMENT", "false")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_predictive_tools",
        type="boolean",
        value=str(os.getenv("ENABLE_PREDICTIVE_TOOLS", "true")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_jira_tools",
        type="boolean",
        value=str(os.getenv("ENABLE_JIRA_TOOLS", "false")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_confluence_tools",
        type="boolean",
        value=str(os.getenv("ENABLE_CONFLUENCE_TOOLS", "false")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_gdrive_tools",
        type="boolean",
        value=str(os.getenv("ENABLE_GDRIVE_TOOLS", "false")).lower(),
    ),
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="enable_microsoft_graph_tools",
        type="boolean",
        value=str(os.getenv("ENABLE_MICROSOFT_GRAPH_TOOLS", "false")).lower(),
    ),
]


# Session secret key credential.
SESSION_SECRET_KEY: Final[str] = "SESSION_SECRET_KEY"

if session_secret_key := os.getenv(SESSION_SECRET_KEY):
    session_secret_cred = pulumi_datarobot.ApiTokenCredential(
        "MCP Server [mcp_server] Session Secret Key",
        args=pulumi_datarobot.ApiTokenCredentialArgs(
            api_token=str(session_secret_key),
        ),
    )
    deployments_model_runtime_parameters.append(
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
            key=SESSION_SECRET_KEY,
            type="credential",
            value=session_secret_cred.id,
        )
    )
    pulumi.export(SESSION_SECRET_KEY, session_secret_key)


# Only add optional OTEL parameters if they have values
if otel_collector_base_url := os.getenv("OTEL_COLLECTOR_BASE_URL"):
    deployments_model_runtime_parameters.append(
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
            key="otel_collector_base_url", type="string", value=otel_collector_base_url
        )
    )

# Only add otel_entity_id if it is provided
if otel_entity_id := os.getenv("OTEL_ENTITY_ID"):
    deployments_model_runtime_parameters.append(
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
            key="otel_entity_id",
            type="string",
            value=otel_entity_id,
        )
    )

# Only add AWS credentials if they are provided
if aws_access_key_id := os.getenv("AWS_ACCESS_KEY_ID"):
    if aws_secret_access_key := os.getenv("AWS_SECRET_ACCESS_KEY"):
        credential = pulumi_datarobot.AwsCredential(
            resource_name=mcp_server_asset_name + " AWS Credential",
            name=mcp_server_asset_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        )
        deployments_model_runtime_parameters.extend(
            [
                pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
                    key="aws_credential", type="credential", value=credential.id
                ),
            ]
        )

if aws_predictions_s3_bucket := os.getenv("AWS_PREDICTIONS_S3_BUCKET"):
    deployments_model_runtime_parameters.append(
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
            key="aws_predictions_s3_bucket",
            type="string",
            value=aws_predictions_s3_bucket,
        )
    )

if aws_predictions_s3_prefix := os.getenv("AWS_PREDICTIONS_S3_PREFIX"):
    deployments_model_runtime_parameters.append(
        pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
            key="aws_predictions_s3_prefix",
            type="string",
            value=aws_predictions_s3_prefix,
        )
    )

# Check if both Google OAuth credentials are provided
is_google_oauth_configured = bool(
    os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")
)

deployments_model_runtime_parameters.append(
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="is_google_oauth_provider_configured",
        type="boolean",
        value=str(is_google_oauth_configured).lower(),
    )
)

# Check if Microsoft OAuth credentials are provided
is_microsoft_oauth_configured = bool(
    os.getenv("MICROSOFT_CLIENT_ID") and os.getenv("MICROSOFT_CLIENT_SECRET")
)

deployments_model_runtime_parameters.append(
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="is_microsoft_oauth_provider_configured",
        type="boolean",
        value=str(is_microsoft_oauth_configured).lower(),
    )
)

# Check if Atlassian OAuth credentials are provided
is_atlassian_oauth_configured = bool(
    os.getenv("ATLASSIAN_CLIENT_ID") and os.getenv("ATLASSIAN_CLIENT_SECRET")
)

deployments_model_runtime_parameters.append(
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="is_atlassian_oauth_provider_configured",
        type="boolean",
        value=str(is_atlassian_oauth_configured).lower(),
    )
)

deployments_model_runtime_parameters.extend(MCP_USER_RUNTIME_PARAMETERS)
custom_model_files = get_deployments_app_files(deployments_model_runtime_parameters)


use_mcp = os.getenv("USE_MCP_TARGET_TYPE", "true").lower() == "true"

if use_mcp:
    pulumi.info("Using MCP target_type")
    target_type = "MCP"
    target_name = None
else:
    pulumi.info("Using unstructured target_type for older environment")
    target_type = "Unstructured"
    target_name = "resultText"

custom_model = pulumi_datarobot.CustomModel(
    resource_name=mcp_server_asset_name + " Custom Model",
    name=mcp_server_asset_name,
    description="MCP server",
    language="python",
    base_environment_id=execution_environment.id,
    base_environment_version_id=execution_environment.version_id,
    target_type=target_type,
    target_name=target_name,
    resource_bundle_id="cpu.small",  # Use API /mlops/compute/bundles/?useCases=customModel to get list of available bundles
    files=custom_model_files,
    use_case_ids=[use_case.id],
    runtime_parameter_values=deployments_model_runtime_parameters,
    tags=[
        pulumi_datarobot.CustomModelTagArgs(
            name="tool",
            value="MCP",
        ),
    ],
)

# Register the custom model so it can be deployed
registerd_model = pulumi_datarobot.RegisteredModel(
    resource_name=mcp_server_asset_name + " Registered Model",
    name=mcp_server_asset_name,
    custom_model_version_id=custom_model.version_id,
    use_case_ids=[use_case.id],
)

# Where to run the custom model
base_prediction_environment = pulumi_datarobot.PredictionEnvironment(
    resource_name=mcp_server_asset_name + " Prediction Environment",
    name=mcp_server_asset_name,
    platform=dr.enums.PredictionEnvironmentPlatform.DATAROBOT_SERVERLESS,
    opts=pulumi.ResourceOptions(retain_on_delete=False),
)

# Deploy the registered custom model
deployment = pulumi_datarobot.Deployment(
    resource_name=mcp_server_asset_name + " Deployment",
    label=mcp_server_asset_name,
    use_case_ids=[use_case.id],
    registered_model_version_id=registerd_model.version_id,
    prediction_environment_id=base_prediction_environment.id,
)

datarobot_endpoint = os.getenv("DATAROBOT_ENDPOINT", "").rstrip("/")
mcp_server_mcp_endpoint = deployment.id.apply(
    lambda id: f"{datarobot_endpoint}/deployments/{id}/directAccess/mcp"
)
mcp_server_base_endpoint = deployment.id.apply(
    lambda id: f"{datarobot_endpoint}/deployments/{id}/directAccess/"
)
pulumi.export(mcp_server_asset_name + " Custom Model Id", custom_model.id)
pulumi.export(mcp_server_asset_name + " Deployment Id", deployment.id)
pulumi.export(
    mcp_server_asset_name + " MCP Server Base Endpoint", mcp_server_base_endpoint
)
pulumi.export(
    mcp_server_asset_name + " MCP Server MCP Endpoint", mcp_server_mcp_endpoint
)

mcp_custom_model_runtime_parameters: list[
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs
] = [
    pulumi_datarobot.CustomModelRuntimeParameterValueArgs(
        key="MCP_DEPLOYMENT_ID",
        type="string",
        value=deployment.id.apply(lambda id: f"{id}"),
    )
]
