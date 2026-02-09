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

import argparse
import os
import sys
from pathlib import Path

from datarobot_drum.drum.adapters.model_adapters import (
    python_model_adapter as _python_model_adapter,
)
from datarobot_drum.drum.root_predictors.prediction_server import PredictionServer

from agent import Config

_original_load_custom_hooks = _python_model_adapter.PythonModelAdapter.load_custom_hooks


def _patched_load_custom_hooks(
    self: _python_model_adapter.PythonModelAdapter,
) -> None:
    custom_file_paths = list(
        Path(self._model_dir).rglob(f"{_python_model_adapter.CUSTOM_FILE_NAME}.py")
    )

    # If there are zero or one files, use the original behavior.
    if len(custom_file_paths) <= 1:
        _original_load_custom_hooks(self)
        return

    # Prefer a custom.py located directly in the model directory, if present.
    root_custom = Path(self._model_dir) / f"{_python_model_adapter.CUSTOM_FILE_NAME}.py"
    if root_custom in custom_file_paths:
        custom_file_path = root_custom
    else:
        # Fallback to original behavior (fail fast) when there's no clear root-level custom.py.
        _original_load_custom_hooks(self)
        return

    self._logger.info("Detected %s .. trying to load hooks", custom_file_path)
    sys.path.insert(0, os.path.dirname(custom_file_path))

    try:
        custom_module = __import__(_python_model_adapter.CUSTOM_FILE_NAME)
        if getattr(custom_module, _python_model_adapter.CUSTOM_PY_CLASS_NAME, None):
            self._load_custom_hooks_for_new_drum(custom_module)
        else:
            self._load_custom_hooks_for_legacy_drum(custom_module)
    except ImportError as exc:
        self._logger.error("Could not load hooks: %s", exc)
        raise


_python_model_adapter.PythonModelAdapter.load_custom_hooks = _patched_load_custom_hooks

parser = argparse.ArgumentParser(description="Run the development server")
parser.add_argument("--autoreload", action="store_true", help="Enable autoreload")

if __name__ == "__main__":
    args = parser.parse_args()

    os.environ["TARGET_NAME"] = "response"
    if args.autoreload:
        os.environ["FLASK_DEBUG"] = "1"

    config = Config()
    port = config.local_dev_port

    # Use absolute path to ensure moderation_config.yaml is found regardless of CWD
    model_path = os.path.dirname(os.path.abspath(__file__))

    print(f"Running development server on http://localhost:{port}")
    PredictionServer(
        {
            "run_language": "python",
            "target_type": "agenticworkflow",
            "deployment_config": None,
            "__custom_model_path__": model_path,
            "port": port,
        }
    ).materialize()
