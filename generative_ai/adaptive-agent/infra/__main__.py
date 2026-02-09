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
* Discover and load all modules with Pulumi resources in the infra directory.
* Discover and validate all required features flags
* Output specially exported variables to a configuration file
"""

from infra import *  # noqa: F403
import importlib
from pathlib import Path
import pulumi
from os import getenv

from datarobot_pulumi_utils.common.feature_flags import check_feature_flags
from datarobot_pulumi_utils.pulumi import default_collector, finalize

CONFIGURATIONS_DIR = Path(__file__).parent / "configurations"
DEFAULT_EXPORT_PATH: Path = Path(
    getenv(
        "PULUMI_EXPORT_PATH", str(Path(__file__).parent.parent / "pulumi_config.json")
    )
)
INFRA_DIR = Path(__file__).parent / "infra"


def toggle_infra_modules():
    """
    Use specialized environment variables to symlink configuration modules from the
    configurations folder into the infra directory. Environment variables follow the
    pattern INFRA_ENABLE_<FOLDER>=<filename> to specify which configuration file
    to use for that folder.

    For example, if you have configurations/llm/external_llm.py and want to use it
    as infra/llm.py, set INFRA_ENABLE_LLM=external_llm.py.
    """
    # Iterate through each configuration folder
    for config_folder in CONFIGURATIONS_DIR.iterdir():
        if not config_folder.is_dir():
            continue

        folder_name = config_folder.name.upper()
        target_module_path = INFRA_DIR / f"{config_folder.name}.py"
        env_var = f"INFRA_ENABLE_{folder_name}"

        # Check if environment variable specifies which configuration to use
        selected_filename = getenv(env_var, "")
        if not selected_filename:
            continue
        selected_config_file = config_folder / selected_filename

        if selected_config_file.exists() and target_module_path.is_symlink():
            target_module_path.unlink()
            relative_path = (
                Path("../configurations") / config_folder.name / selected_filename
            )
            target_module_path.symlink_to(relative_path)
        else:
            pulumi.error(
                f"Configuration file {selected_config_file} does not exist or target module {target_module_path} is not a symlink."
            )


def import_infra_modules():
    """
    Dynamically import all top-level modules in the infra package.
    This function is executed after the initial import from __init__.
    """
    infra_dir = Path(__file__).parent / "infra"
    # Get all Python files in the infra directory
    for file_path in infra_dir.glob("*.py"):
        filename = file_path.name
        if filename == "__init__.py" or filename == "__main__.py":
            continue

        # Import a module by its filename and bring its contents into the current namespace
        module_name = f"infra.{filename[:-3]}"
        # Import the module
        module = importlib.import_module(module_name)

        # Import all from the module to the current namespace
        for attr in dir(module):
            if attr.startswith("_"):  # Skip private attributes
                continue
            globals()[attr] = getattr(module, attr)


def check_all_feature_flags():
    """
    Discover and check all feature flag files in the infra directory.

    See the README.md in the `feature_flags` folder for more detail and example
    feature flag file examples.
    """
    infra_dir = Path(__file__).parent / "feature_flags"
    for feature_flag_file in infra_dir.glob("*.y*ml"):
        if feature_flag_file.is_file():
            check_feature_flags(feature_flag_file)


# Validate all feature flags
check_all_feature_flags()

# Toggle infra modules based on environment variables
toggle_infra_modules()

# Import all non-disabled modules
import_infra_modules()

# Export outputs using datarobot_pulumi_utils.pulumi.export to a JSON
# file for use in local development.
default_collector.output_path = DEFAULT_EXPORT_PATH
finalize()
