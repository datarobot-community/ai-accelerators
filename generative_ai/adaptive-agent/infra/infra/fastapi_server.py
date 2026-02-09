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
from typing import Any, Final, Optional, Sequence

import datarobot
import pulumi
import pulumi_datarobot
from datarobot_pulumi_utils.schema.apps import ApplicationSourceArgs
from datarobot_pulumi_utils.schema.apps import CustomAppResourceBundles
from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments
from datarobot_pulumi_utils.pulumi.stack import PROJECT_NAME


from . import project_dir, use_case
from .frontend_web import frontend_web
from .llm import app_runtime_parameters as llm_app_runtime_parameters
from .oauth import app_runtime_parameters as oauth_app_runtime_parameters
from .agent import agent_app_runtime_parameters


SESSION_SECRET_KEY: Final[str] = "SESSION_SECRET_KEY"
session_secret_key = os.environ.get(SESSION_SECRET_KEY)

required_key_scope_level: str = "admin"

EXCLUDE_PATTERNS = [
    re.compile(pattern)
    for pattern in [
        r".*tests/.*",
        r".*\.coverage",
        r".*\.DS_Store",
        r".*\.pyc",
        r".*\.ruff_cache/.*",
        r".*\.venv/.*",
        r".*\.mypy_cache/.*",
        r".*__pycache__/.*",
        r".*\.pytest_cache/.*",
        r".*htmlcov/.*",
        r".*\.data/.*",
        r".*\.env",
    ]
]


__all__ = [
    "fastapi_server_app",
    "fastapi_server_app_env_name",
    "fastapi_server_app_resource_name",
    "fastapi_server_app_runtime_parameters",
    "fastapi_server_app_source",
    "fastapi_server_application_path",
    "get_fastapi_server_app_files",
]


def fetch_and_prepare_app_resources(source_id: str) -> Optional[dict[str, Any]]:
    """
    Fetch resource configuration from a CustomApplicationSource entity
    and prepare it for CustomApplication creation.

    Args:
        source_id: The ID of the CustomApplicationSource to fetch resources from

    Returns:
        Dictionary containing resource configuration compatible with CustomApplication,
        or None if not configured
    """
    try:
        source = datarobot.CustomApplicationSource.get(source_id)
        pulumi.info(f"Fetched CustomApplicationSource: {source.name} (ID: {source.id})")

        resources = source.get_resources()
        if resources:
            pulumi.info(f"Found resources in source: {resources}")
            # Prepare resources in the format expected by CustomApplication
            app_resources = {
                "resource_label": resources.get("resource_label"),
                "replicas": resources.get("replicas"),
            }
            # Optional fields - only include if present
            if resources.get("session_affinity") is not None:
                app_resources["session_affinity"] = resources.get("session_affinity")
            if resources.get("service_web_requests_on_root_path") is not None:
                app_resources["service_web_requests_on_root_path"] = resources.get(
                    "service_web_requests_on_root_path"
                )
            return app_resources
        else:
            pulumi.warn("No resources configured in CustomApplicationSource")
            return None
    except Exception as e:
        pulumi.warn(f"Failed to fetch resources from CustomApplicationSource: {e}")
        return None


def create_resources_args(
    source_id: str,
) -> pulumi_datarobot.CustomApplicationResourcesArgs | dict[str, Any]:
    """
    Fetch resources from source and convert to Pulumi CustomApplicationResourcesArgs.

    Args:
        source_id: The ID of the CustomApplicationSource

    Returns:
        CustomApplicationResourcesArgs if resources exist, empty dict otherwise
    """
    resources = fetch_and_prepare_app_resources(source_id)
    if resources:
        return pulumi_datarobot.CustomApplicationResourcesArgs(**resources)
    return {}


def _prep_metadata_yaml(
    runtime_parameter_values: Sequence[
        pulumi_datarobot.ApplicationSourceRuntimeParameterValueArgs
        | pulumi_datarobot.CustomModelRuntimeParameterValueArgs
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
    with open(fastapi_server_application_path / "metadata.yaml.jinja") as f:
        template = Environment(loader=BaseLoader()).from_string(f.read())
    (fastapi_server_application_path / "metadata.yaml").write_text(
        template.render(
            additional_params=runtime_parameter_specs,
        )
    )


def get_fastapi_server_app_files(
    runtime_parameter_values: Sequence[
        pulumi_datarobot.ApplicationSourceRuntimeParameterValueArgs
        | pulumi_datarobot.CustomModelRuntimeParameterValueArgs,
    ],
) -> list[tuple[str, str]]:
    _prep_metadata_yaml(runtime_parameter_values)
    # Get all files from application path, following symlinks
    # When we've upgraded to Python 3.13 we can use Path.glob(reduce_symlinks=True)
    # https://docs.python.org/3.13/library/pathlib.html#pathlib.Path.glob
    source_files = []
    for dirpath, dirnames, filenames in os.walk(
        fastapi_server_application_path, followlinks=True
    ):
        for filename in filenames:
            if filename == "metadata.yaml":
                continue
            file_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(file_path, fastapi_server_application_path)
            # Convert to forward slashes for Linux destination
            rel_path = rel_path.replace(os.path.sep, "/")
            source_files.append((os.path.abspath(file_path), rel_path))
    # Add the metadata.yaml file
    source_files.append(
        (
            (fastapi_server_application_path / "metadata.yaml").as_posix(),
            "metadata.yaml",
        )
    )
    source_files = [
        (file_path, file_name)
        for file_path, file_name in source_files
        if not any(
            exclude_pattern.match(file_name) for exclude_pattern in EXCLUDE_PATTERNS
        )
    ]
    return source_files


# Start of Pulumi settings and application infrastructure
pulumi.export("SESSION_SECRET_KEY", session_secret_key)
session_secret_cred = pulumi_datarobot.ApiTokenCredential(
    f"Agentic Application Starter Session Secret Key [{PROJECT_NAME}]",
    args=pulumi_datarobot.ApiTokenCredentialArgs(
        api_token=str(session_secret_key),
    ),
)
fastapi_server_app_env_name: str = "DATAROBOT_APPLICATION_ID"
fastapi_server_application_path = project_dir.parent / "fastapi_server"

fastapi_server_app_source_args = ApplicationSourceArgs(
    resource_name=f"Agentic Application Starter [{PROJECT_NAME}]",
    base_environment_id=RuntimeEnvironments.PYTHON_312_APPLICATION_BASE.value.id,
).model_dump(mode="json", exclude_none=True)

fastapi_server_app_resource_name: str = f"Agentic Application Starter [{PROJECT_NAME}]"
fastapi_server_app_runtime_parameters: list[
    pulumi_datarobot.ApplicationSourceRuntimeParameterValueArgs
] = (
    agent_app_runtime_parameters
    + llm_app_runtime_parameters
    + [
        parameter
        for parameter_group in [
            oauth_app_runtime_parameters,
        ]
        for parameter in parameter_group
    ]
    + [
        pulumi_datarobot.ApplicationSourceRuntimeParameterValueArgs(
            type="credential",
            key=SESSION_SECRET_KEY,
            value=session_secret_cred.id,
        ),
    ]
)

fastapi_server_app_source = pulumi_datarobot.ApplicationSource(
    files=frontend_web.stdout.apply(
        lambda _: get_fastapi_server_app_files(
            runtime_parameter_values=fastapi_server_app_runtime_parameters
        )
    ),
    runtime_parameter_values=fastapi_server_app_runtime_parameters,
    resources=pulumi_datarobot.ApplicationSourceResourcesArgs(
        resource_label=CustomAppResourceBundles.CPU_XL.value.id,
    ),
    required_key_scope_level=required_key_scope_level,
    **fastapi_server_app_source_args,
)

fastapi_server_app = pulumi_datarobot.CustomApplication(
    resource_name=fastapi_server_app_resource_name,
    source_version_id=fastapi_server_app_source.version_id,
    use_case_ids=[use_case.id],
    allow_auto_stopping=True,
    resources=fastapi_server_app_source.id.apply(create_resources_args),
    required_key_scope_level=fastapi_server_app_source.required_key_scope_level,
    opts=pulumi.ResourceOptions(depends_on=[fastapi_server_app_source]),
)

pulumi.export(fastapi_server_app_env_name, fastapi_server_app.id)
pulumi.export(
    fastapi_server_app_resource_name,
    fastapi_server_app.application_url,
)

DATABASE_URI: Final[str] = "DATABASE_URI"
database_uri = os.environ.get(
    DATABASE_URI, "sqlite+aiosqlite:////tmp/agent_app/.data/agent_app.db"
)

pulumi.export("DATABASE_URI", database_uri)

database_uri_cred = pulumi_datarobot.ApiTokenCredential(
    f"Agentic Application Starter Database URI [{PROJECT_NAME}]",
    args=pulumi_datarobot.ApiTokenCredentialArgs(
        api_token=str(database_uri),
    ),
)
