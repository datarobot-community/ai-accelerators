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
import sys
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

# Ensure the test directory is in sys.path for proper imports
sys.path.insert(0, str(Path(__file__).resolve().parent))


# Patch all Pulumi resources and functions used in the module
@pytest.fixture(autouse=True)
def pulumi_mocks(monkeypatch, tmp_path):
    # Mock infra.__init__ exported objects
    mock_use_case = MagicMock()
    mock_use_case.id = "mock-use-case-id"
    mock_project_dir = tmp_path
    monkeypatch.setattr("infra.use_case", mock_use_case)
    monkeypatch.setattr("infra.project_dir", mock_project_dir)

    # Mock out the LLM and just expose the runtime parameters as it is the only public
    # interface required for this module.
    mock_llm_module = MagicMock()
    mock_llm_module.custom_model_runtime_parameters = []
    monkeypatch.setitem(sys.modules, "infra.llm", mock_llm_module)
    # Mock out the MCP Server and just expose the runtime parameters as it is the only public
    # interface required for this module.
    mock_mcp_module = MagicMock()
    mock_mcp_module.mcp_custom_model_runtime_parameters = []
    monkeypatch.setitem(sys.modules, "infra.mcp_server", mock_mcp_module)
    # Mock pulumi_datarobot resources
    monkeypatch.setattr("pulumi_datarobot.ExecutionEnvironment", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.CustomModel", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.ApiTokenCredential", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.ApiTokenCredentialArgs", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.Playground", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.LlmBlueprint", MagicMock())
    monkeypatch.setattr("pulumi_datarobot.PredictionEnvironment", MagicMock())
    monkeypatch.setattr(
        "pulumi_datarobot.DeploymentAssociationIdSettingsArgs", MagicMock()
    )
    monkeypatch.setattr(
        "pulumi_datarobot.DeploymentPredictionsDataCollectionSettingsArgs", MagicMock()
    )
    monkeypatch.setattr(
        "pulumi_datarobot.DeploymentPredictionsSettingsArgs", MagicMock()
    )
    monkeypatch.setattr(
        "pulumi_datarobot.ApplicationSourceRuntimeParameterValueArgs", MagicMock()
    )

    # Patch the id property of the RuntimeEnvironment instance for PYTHON_311_GENAI_AGENTS
    from datarobot_pulumi_utils.schema.exec_envs import RuntimeEnvironments

    patcher = patch.object(
        RuntimeEnvironments.PYTHON_311_GENAI_AGENTS.value.__class__,
        "id",
        new_callable=PropertyMock,
        return_value="python-311-genai-agents-id",
    )
    patcher.start()

    # Mock pulumi functions
    monkeypatch.setattr("pulumi.export", MagicMock())
    monkeypatch.setattr("pulumi.info", MagicMock())

    # Mock CustomModelDeployment
    monkeypatch.setattr(
        "datarobot_pulumi_utils.pulumi.custom_model_deployment.CustomModelDeployment",
        MagicMock(),
    )

    # Mock Output to behave like a Pulumi Output with .apply(), support subscript notation, and from_input
    class MockOutput(MagicMock):
        def __new__(cls, val=None, *args, **kwargs):
            m = super().__new__(cls)
            m.apply = MagicMock(side_effect=lambda fn: fn(val))
            return m

        @classmethod
        def __class_getitem__(cls, item):
            return cls

    # Set from_input() and format() as class methods that can be tracked
    MockOutput.from_input = MagicMock()
    MockOutput.format = MagicMock()
    monkeypatch.setattr("pulumi.Output", MockOutput)

    yield
    patcher.stop()


def test_execution_environment_not_set_and_docker_context(monkeypatch):
    """Test execution environment creation when DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT is not set"""
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)

    import importlib
    import infra.agent as agent_infra

    # Reset the mock to clear calls from the initial import
    agent_infra.pulumi_datarobot.ExecutionEnvironment.reset_mock()
    agent_infra.pulumi.info.reset_mock()
    importlib.reload(agent_infra)

    # Check that pulumi.info was called with the correct message for docker_context.tar.gz
    agent_infra.pulumi.info.assert_any_call(
        "Using docker_context folder to compile the execution environment"
    )

    # Check that ExecutionEnvironment constructor was called correctly
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.ExecutionEnvironment.call_args

    assert kwargs["resource_name"] == "[unittest] [agent] Execution Environment"
    assert kwargs["programming_language"] == "python"
    assert kwargs["name"] == "[unittest] [agent] Execution Environment"
    assert kwargs["description"] == "Execution Environment for [unittest] [agent]"  # fmt: skip
    assert "docker_context_path" in kwargs
    assert "docker_image" not in kwargs
    assert kwargs["use_cases"] == ["customModel", "notebook"]

    # ExecutionEnvironment.get should not be called when env var is not set
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_not_called()


def test_execution_environment_not_set_with_docker_image(monkeypatch):
    """Test execution environment creation when DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT is not set and docker_context.tar.gz exists"""
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)

    # Mock os.path.exists to return True for docker_context.tar.gz
    def mock_exists(path):
        if path.endswith("docker_context.tar.gz"):
            return True
        return False

    monkeypatch.setattr("os.path.exists", mock_exists)

    import importlib
    import infra.agent as agent_infra

    # Reset the mock to clear calls from the initial import
    agent_infra.pulumi_datarobot.ExecutionEnvironment.reset_mock()
    agent_infra.pulumi.info.reset_mock()
    importlib.reload(agent_infra)

    # Check that pulumi.info was called with the correct message for docker_context.tar.gz
    agent_infra.pulumi.info.assert_any_call(
        "Using prebuilt Dockerfile docker_context.tar.gz to run the execution environment"
    )

    # Check that ExecutionEnvironment constructor was called correctly
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.ExecutionEnvironment.call_args

    assert kwargs["resource_name"] == "[unittest] [agent] Execution Environment"
    assert kwargs["programming_language"] == "python"
    assert kwargs["name"] == "[unittest] [agent] Execution Environment"
    assert kwargs["description"] == "Execution Environment for [unittest] [agent]"  # fmt: skip
    assert "docker_image" in kwargs
    assert "docker_context_path" not in kwargs
    assert kwargs["use_cases"] == ["customModel", "notebook"]

    # ExecutionEnvironment.get should not be called when env var is not set
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_not_called()


def test_execution_environment_default_set(monkeypatch):
    """Test execution environment when DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT is set to default value"""
    monkeypatch.setenv(
        "DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT",
        "[DataRobot] Python 3.11 GenAI Agents",
    )

    import importlib
    import infra.agent as agent_infra

    importlib.reload(agent_infra)

    # Check that pulumi.info was called with the correct message
    agent_infra.pulumi.info.assert_any_call(
        "Using default GenAI Agentic Execution Environment."
    )
    agent_infra.pulumi.info.assert_any_call(
        "No valid execution environment version ID provided, using latest version."
    )

    # Check that ExecutionEnvironment.get was called with the correct parameters
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.ExecutionEnvironment.get.call_args

    assert kwargs["id"] == "python-311-genai-agents-id"
    assert kwargs["version_id"] is None
    assert kwargs["resource_name"] == "[unittest] [agent] Execution Environment"

    # ExecutionEnvironment constructor should not be called when using default env
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_not_called()


def test_execution_environment_pinned_set(monkeypatch):
    """Test execution environment when DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT is set to default value"""
    monkeypatch.setenv(
        "DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT",
        "[DataRobot] Python 3.11 GenAI Agents",
    )
    monkeypatch.setenv(
        "DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT_VERSION_ID",
        "690cd2f698419673f938f7c4",
    )

    import importlib
    import infra.agent as agent_infra

    importlib.reload(agent_infra)

    # Check that pulumi.info was called with the correct message
    agent_infra.pulumi.info.assert_any_call(
        "Using default GenAI Agentic Execution Environment."
    )
    agent_infra.pulumi.info.assert_any_call(
        "Using existing execution environment: python-311-genai-agents-id Version ID: 690cd2f698419673f938f7c4"
    )

    # Check that ExecutionEnvironment.get was called with the correct parameters
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.ExecutionEnvironment.get.call_args

    assert kwargs["id"] == "python-311-genai-agents-id"
    assert kwargs["version_id"] == "690cd2f698419673f938f7c4"
    assert kwargs["resource_name"] == "[unittest] [agent] Execution Environment"

    # ExecutionEnvironment constructor should not be called when using default env
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_not_called()


def test_execution_environment_custom_set(monkeypatch):
    """Test execution environment when DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT is set to a custom value"""
    monkeypatch.setenv(
        "DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", "Custom Execution Environment"
    )

    import importlib
    import infra.agent as agent_infra

    importlib.reload(agent_infra)

    # Check that pulumi.info was called with the correct message
    agent_infra.pulumi.info.assert_any_call(
        "No valid execution environment version ID provided, using latest version."
    )
    agent_infra.pulumi.info.assert_any_call(
        "Using existing execution environment: Custom Execution Environment Version ID: None"
    )

    # Check that ExecutionEnvironment.get was called with the correct parameters
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.ExecutionEnvironment.get.call_args

    assert kwargs["id"] == "Custom Execution Environment"
    assert kwargs["version_id"] is None
    assert kwargs["resource_name"] == "[unittest] [agent] Execution Environment"

    # ExecutionEnvironment constructor should not be called when using custom env
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_not_called()


def test_reset_environment_between_tests():
    """Test to ensure that environment variables don't leak between tests"""
    # This test should run with no environment variables set from previous tests
    assert os.environ.get("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT") is None

    import importlib
    import infra.agent as agent_infra

    importlib.reload(agent_infra)

    # Default behavior should be to create a new execution environment
    agent_infra.pulumi_datarobot.ExecutionEnvironment.assert_called_once()
    agent_infra.pulumi_datarobot.ExecutionEnvironment.get.assert_not_called()


def test_custom_model_created(monkeypatch):
    """Test that pulumi_datarobot.CustomModel is created with correct arguments."""
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)

    import importlib
    import infra.agent as agent_infra

    # Reset the mock to clear calls from the initial import
    agent_infra.pulumi_datarobot.CustomModel.reset_mock()

    environment_variables = {
        "SESSION_SECRET_KEY": "secret_value",
    }
    with patch.dict(os.environ, environment_variables):
        importlib.reload(agent_infra)

    agent_infra.pulumi_datarobot.CustomModel.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.CustomModel.call_args
    assert kwargs["resource_name"] == "[unittest] [agent] Custom Model"
    assert kwargs["name"] == "[unittest] [agent] Custom Model"
    assert kwargs["base_environment_id"] == agent_infra.agent_execution_environment.id  # fmt: skip
    assert (
        kwargs["base_environment_version_id"]
        == agent_infra.agent_execution_environment.version_id
    )
    assert kwargs["target_type"] == "AgenticWorkflow"
    assert kwargs["target_name"] == "response"
    assert kwargs["language"] == "python"
    assert kwargs["use_case_ids"] == [agent_infra.use_case.id]
    assert isinstance(kwargs["files"], list)

    runtime_parameter_values = kwargs["runtime_parameter_values"]

    assert len(runtime_parameter_values) == 1
    assert runtime_parameter_values[0].type == "credential"
    assert runtime_parameter_values[0].key == "SESSION_SECRET_KEY"
    assert runtime_parameter_values[0].value is not None


def test_custom_model_created_pinned_version_id(monkeypatch):
    """Test that pulumi_datarobot.CustomModel is created with correct arguments."""
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)
    monkeypatch.setenv(
        "DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT_VERSION_ID", "690cd2f698419673f938f7c4"
    )
    monkeypatch.setattr(
        "pulumi_datarobot.ExecutionEnvironment",
        MagicMock(
            return_value=MagicMock(
                id="default-id", version_id="690cd2f698419673f938f7c4"
            )
        ),
    )

    import importlib
    import infra.agent as agent_infra

    # Reset the mock to clear calls from the initial import
    agent_infra.pulumi_datarobot.CustomModel.reset_mock()

    environment_variables = {
        "SESSION_SECRET_KEY": "secret_value",
    }
    with patch.dict(os.environ, environment_variables):
        importlib.reload(agent_infra)

    agent_infra.pulumi_datarobot.CustomModel.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.CustomModel.call_args
    assert kwargs["base_environment_id"] == "default-id"
    assert kwargs["base_environment_version_id"] == "690cd2f698419673f938f7c4"


def test_agentic_playground_and_blueprint_created(monkeypatch):
    """Test that pulumi_datarobot.Playground and pulumi_datarobot.LlmBlueprint are created
    and the Playground URL is added to outputs."""
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)
    monkeypatch.setenv("DATAROBOT_ENDPOINT", "https://example.datarobot.com/api/v2")

    import importlib
    import infra.agent as agent_infra

    # Reset the mocks to clear calls from the initial import
    agent_infra.pulumi_datarobot.Playground.reset_mock()
    agent_infra.pulumi_datarobot.LlmBlueprint.reset_mock()
    agent_infra.pulumi.export.reset_mock()
    importlib.reload(agent_infra)

    # Check that Agentic Playground was created
    agent_infra.pulumi_datarobot.Playground.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.Playground.call_args
    assert kwargs["resource_name"] == "[unittest] [agent] Agentic Playground"
    assert kwargs["name"] == "[unittest] [agent] Agentic Playground"
    assert kwargs["use_case_id"] == agent_infra.use_case.id
    assert kwargs["playground_type"] == "agentic"

    # Check that LlmBlueprint was created and points to the created custom model
    agent_infra.pulumi_datarobot.LlmBlueprint.assert_called_once()
    args, kwargs = agent_infra.pulumi_datarobot.LlmBlueprint.call_args
    assert kwargs["resource_name"] == "[unittest] [agent] LLM Blueprint"
    assert kwargs["name"] == "[unittest] [agent] LLM Blueprint"
    assert kwargs["llm_id"] == "chat-interface-custom-model"
    assert kwargs["prompt_type"] == "ONE_TIME_PROMPT"
    assert kwargs[
        "llm_settings"
    ] == agent_infra.pulumi_datarobot.LlmBlueprintLlmSettingsArgs(
        custom_model_id=agent_infra.agent_custom_model.id
    )

    # Check that we export agent Playground URL from pulumi
    export_names = [call.args[0] for call in agent_infra.pulumi.export.call_args_list]
    assert "Agent Playground URL " + agent_infra.agent_asset_name in export_names  # fmt: skip

    # Check the format of the URL
    agent_infra.pulumi.Output.format.assert_any_call(
        "{0}/usecases/{1}/agentic-playgrounds/{2}/comparison/chats",
        "https://example.datarobot.com",
        "mock-use-case-id",
        agent_infra.agent_playground.id,
    )


def test_agent_deployment_created_when_env(monkeypatch):
    """Test that agent deployment resources are created when AGENT_DEPLOY is not '0'."""
    monkeypatch.setenv("AGENT_DEPLOY", "1")
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)

    import importlib
    import infra.agent as agent_infra

    # Reset mocks to clear calls from the initial import
    agent_infra.pulumi_datarobot.PredictionEnvironment.reset_mock()
    agent_infra.pulumi_datarobot.DeploymentAssociationIdSettingsArgs.reset_mock()
    agent_infra.pulumi_datarobot.DeploymentPredictionsDataCollectionSettingsArgs.reset_mock()
    agent_infra.pulumi_datarobot.DeploymentPredictionsSettingsArgs.reset_mock()
    agent_infra.CustomModelDeployment.reset_mock()
    importlib.reload(agent_infra)

    # Check that PredictionEnvironment was created
    agent_infra.pulumi_datarobot.PredictionEnvironment.assert_called_once()
    # Check that CustomModelDeployment was created
    agent_infra.CustomModelDeployment.assert_called_once()
    agent_infra.pulumi.export.assert_any_call(
        "Agent Deployment Chat Endpoint " + agent_infra.agent_asset_name,
        agent_infra.CustomModelDeployment.return_value.id.apply.return_value,
    )


def test_agent_deployment_not_created_when_env_zero(monkeypatch):
    """Test that agent deployment resources are not created when AGENT_DEPLOY is '0'."""
    monkeypatch.setenv("AGENT_DEPLOY", "0")
    monkeypatch.delenv("DATAROBOT_DEFAULT_EXECUTION_ENVIRONMENT", raising=False)

    import importlib
    import infra.agent as agent_infra

    # Reset mocks to clear calls from the initial import
    agent_infra.pulumi_datarobot.PredictionEnvironment.reset_mock()
    agent_infra.CustomModelDeployment.reset_mock()
    importlib.reload(agent_infra)

    # Check that PredictionEnvironment and CustomModelDeployment were not called
    agent_infra.pulumi_datarobot.PredictionEnvironment.assert_not_called()
    agent_infra.CustomModelDeployment.assert_not_called()


class TestGetCustomModelFiles:
    def test_get_custom_model_files_basic(self, tmp_path):
        import infra.agent as agent_infra

        # Create a simple file structure
        (tmp_path / "file1.py").write_text("print('hi')")
        (tmp_path / "file2.txt").write_text("hello")
        files = agent_infra.get_custom_model_files(str(tmp_path), [])
        file_names = [f[1] for f in files]
        assert "file1.py" in file_names
        assert "file2.txt" in file_names

        # Autogenerated metadata file
        assert "model-metadata.yaml" in file_names
        assert len(files) == 3

    def test_get_custom_model_files_excludes(self, tmp_path):
        import infra.agent as agent_infra

        # Create files that should be excluded
        (tmp_path / "file1.py").write_text("print('hi')")
        (tmp_path / ".DS_Store").write_text("")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "foo.pyc").write_text("")
        files = agent_infra.get_custom_model_files(str(tmp_path), [])
        file_names = [f[1] for f in files]
        assert "file1.py" in file_names
        assert ".DS_Store" not in file_names
        assert "__pycache__/foo.pyc" not in file_names

        # Autogenerated metadata file
        assert "model-metadata.yaml" in file_names
        assert len(files) == 2

    def test_get_custom_model_files_excludes_docker_context(self, tmp_path):
        import infra.agent as agent_infra

        # Create files including a docker_context directory that should be excluded
        (tmp_path / "file1.py").write_text("print('hi')")
        docker_context_dir = tmp_path / "docker_context"
        docker_context_dir.mkdir()
        (docker_context_dir / "docker_file.py").write_text("print('docker')")

        files = agent_infra.get_custom_model_files(str(tmp_path), [])
        file_names = [f[1] for f in files]

        assert "file1.py" in file_names
        assert "docker_context/docker_file.py" not in file_names

    def test_get_custom_model_files_symlinks(self, tmp_path):
        import infra.agent as agent_infra

        # Create a real file and a symlink to it
        real_file = tmp_path / "real.py"
        real_file.write_text("print('hi')")
        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.mkdir()
        symlink = symlink_dir / "link.py"
        symlink.symlink_to(real_file)
        files = agent_infra.get_custom_model_files(str(tmp_path), [])
        file_names = [f[1] for f in files]
        assert "real.py" in file_names


class TestSynchronizePyprojectDependencies:
    def test_synchronize_pyproject_dependencies_basic(self, tmp_path, monkeypatch):
        import infra.agent as agent_infra

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create pyproject.toml in the application path
        pyproject_content = """[project]
name = "test-project"
dependencies = ["requests>=2.0"]
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)
        (tmp_path / "uv.lock").write_text("test content")

        # Create docker_context directory
        (tmp_path / "docker_context").mkdir()

        # Call the function
        agent_infra.synchronize_pyproject_dependencies()

        # Check that pyproject.toml was copied to docker_context
        assert (tmp_path / "docker_context" / "pyproject.toml").exists()
        assert (tmp_path / "docker_context" / "uv.lock").exists()

        # Verify the content is the same
        assert (
            tmp_path / "docker_context" / "pyproject.toml"
        ).read_text() == pyproject_content
        assert (tmp_path / "docker_context" / "uv.lock").read_text() == "test content"

    def test_synchronize_pyproject_dependencies_no_pyproject(
        self, tmp_path, monkeypatch
    ):
        import infra.agent as agent_infra

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create docker_context directory but no pyproject.toml
        (tmp_path / "docker_context").mkdir()

        # Call the function - should return early without error
        agent_infra.synchronize_pyproject_dependencies()

        # Check that no pyproject.toml files were created
        assert not (tmp_path / "docker_context" / "pyproject.toml").exists()

    def test_synchronize_pyproject_dependencies_missing_docker_context_dir(
        self, tmp_path, monkeypatch
    ):
        import infra.agent as agent_infra

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create pyproject.toml but not docker_context
        pyproject_content = """[project]
name = "test-project"
"""
        (tmp_path / "pyproject.toml").write_text(pyproject_content)

        # Call the function
        agent_infra.synchronize_pyproject_dependencies()

        # Check that no docker_context directory was created
        assert not (tmp_path / "docker_context").exists()

    def test_synchronize_pyproject_dependencies_overwrites_existing(
        self, tmp_path, monkeypatch
    ):
        import infra.agent as agent_infra

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create pyproject.toml in the application path
        new_content = """[project]
name = "updated-project"
dependencies = ["requests>=3.0"]
"""
        (tmp_path / "pyproject.toml").write_text(new_content)

        # Create docker_context directory with existing pyproject.toml file
        (tmp_path / "docker_context").mkdir()

        old_content = """[project]
name = "old-project"
"""
        (tmp_path / "docker_context" / "pyproject.toml").write_text(old_content)

        # Call the function
        agent_infra.synchronize_pyproject_dependencies()

        # Check that the old file was overwritten with new content
        assert (
            tmp_path / "docker_context" / "pyproject.toml"
        ).read_text() == new_content


class TestMaybeImportFromModule:
    @pytest.fixture
    def skip_if_no_mcp(self):
        """Skip tests if mcp module is not available."""
        mcp_module = "mcp_server"
        if not mcp_module:
            pytest.skip("Skipping tests of existing MCP when module is not provided.")

    @pytest.mark.usefixtures("skip_if_no_mcp")
    def test_maybe_import_from_module_success(self):
        """Test that maybe_import_from_module successfully imports an existing module."""
        import infra.agent as agent_infra

        # The fixture sets up the mocked MCP module with mcp_custom_model_runtime_parameters
        result = agent_infra.maybe_import_from_module(
            "mcp_server", "mcp_custom_model_runtime_parameters"
        )
        assert result is not None

    def test_maybe_import_from_module_missing_module(self, monkeypatch):
        """Test that maybe_import_from_module returns None when module is not available."""
        import infra.agent as agent_infra

        # Mock importlib.import_module to raise ImportError
        def mock_import_module(name, package=None):
            raise ImportError(f"No module named '{name}'")

        monkeypatch.setattr("importlib.import_module", mock_import_module)

        # Attempt to import from the non-existent module
        result = agent_infra.maybe_import_from_module(
            "mcp_server", "mcp_custom_model_runtime_parameters"
        )
        assert result is None

    def test_maybe_import_from_module_empty_module_name(self):
        """Test that maybe_import_from_module returns None with empty module name."""
        import infra.agent as agent_infra

        result = agent_infra.maybe_import_from_module("", "some_attribute")
        assert result is None


class TestGetMcpCustomModelRuntimeParameters:
    def test_get_mcp_custom_model_runtime_parameters_from_module(self):
        """Test that MCP runtime parameters are loaded from the module when available."""
        import infra.agent as agent_infra

        result = agent_infra.get_mcp_custom_model_runtime_parameters()
        # The fixture sets up a mock module with empty list
        assert isinstance(result, list)

    def test_get_mcp_custom_model_runtime_parameters_fallback_to_env(self, monkeypatch):
        """Test that MCP runtime parameters fall back to environment variables when module is unavailable."""
        import infra.agent as agent_infra

        # Set up environment variables
        monkeypatch.setenv("MCP_DEPLOYMENT_ID", "test-deployment-123")
        monkeypatch.setenv("EXTERNAL_MCP_URL", "https://example.com/mcp")
        monkeypatch.setenv(
            "EXTERNAL_MCP_HEADERS", '{"Authorization": "Bearer token123"}'
        )
        monkeypatch.setenv("EXTERNAL_MCP_TRANSPORT", "sse")

        # Mock importlib.import_module to raise ImportError
        def mock_import_module(name, package=None):
            raise ImportError(f"No module named '{name}'")

        monkeypatch.setattr("importlib.import_module", mock_import_module)

        # Get runtime parameters - should fall back to environment variables
        result = agent_infra.get_mcp_custom_model_runtime_parameters()

        assert isinstance(result, list)
        assert len(result) == 4

        # Check MCP_DEPLOYMENT_ID parameter
        mcp_deployment_param = next(
            (p for p in result if p.key == "MCP_DEPLOYMENT_ID"), None
        )
        assert mcp_deployment_param is not None
        assert mcp_deployment_param.type == "string"
        assert mcp_deployment_param.value == "test-deployment-123"

        # Check EXTERNAL_MCP_URL parameter
        external_mcp_param = next(
            (p for p in result if p.key == "EXTERNAL_MCP_URL"), None
        )
        assert external_mcp_param is not None
        assert external_mcp_param.type == "string"
        assert external_mcp_param.value == "https://example.com/mcp"

        # Check EXTERNAL_MCP_HEADERS parameter
        external_mcp_headers_param = next(
            (p for p in result if p.key == "EXTERNAL_MCP_HEADERS"), None
        )
        assert external_mcp_headers_param is not None
        assert external_mcp_headers_param.type == "string"
        assert external_mcp_headers_param.value == (
            '{"Authorization": "Bearer token123"}'
        )

        # Check EXTERNAL_MCP_TRANSPORT parameter
        external_mcp_transport_param = next(
            (p for p in result if p.key == "EXTERNAL_MCP_TRANSPORT"), None
        )
        assert external_mcp_transport_param is not None
        assert external_mcp_transport_param.type == "string"
        assert external_mcp_transport_param.value == "sse"


class TestGenerateMetadataYaml:
    def test_mixed_parameters(self, tmp_path, monkeypatch):
        """Test _generate_metadata_yaml with string and credential parameters, including special characters."""
        import infra.agent as agent_infra
        import yaml  # type: ignore[import-untyped]

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create mixed runtime parameters with special characters
        mock_params = [
            MagicMock(key="LLM_DEPLOYMENT_ID", type="string"),
            MagicMock(key="SESSION_SECRET_KEY", type="credential"),
            MagicMock(key="PARAM_WITH_UNDERSCORE_123", type="string"),
        ]

        # Call the function with tmp_path as the custom model folder
        agent_infra._generate_metadata_yaml("agent", str(tmp_path), mock_params)

        # Read and parse the generated YAML
        metadata_file = tmp_path / "model-metadata.yaml"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)

        # Verify metadata structure
        assert metadata["name"] == "agent"
        assert metadata["type"] == "inference"
        assert metadata["targetType"] == "agenticworkflow"

        # Verify parameters maintain order and correct types
        params = metadata["runtimeParameterDefinitions"]
        assert len(params) == 3

        # String parameter with defaultValue
        assert params[0]["fieldName"] == "LLM_DEPLOYMENT_ID"
        assert params[0]["type"] == "string"
        assert "defaultValue" not in params[0]

        # Credential parameter without defaultValue
        assert params[1]["fieldName"] == "SESSION_SECRET_KEY"
        assert params[1]["type"] == "credential"
        assert "defaultValue" not in params[1]
        assert "credentialType" not in params[1]

        # String parameter with special characters
        assert params[2]["fieldName"] == "PARAM_WITH_UNDERSCORE_123"
        assert params[2]["type"] == "string"
        assert "defaultValue" not in params[2]

    def test_with_empty_parameters(self, tmp_path, monkeypatch):
        """Test _generate_metadata_yaml generates correct YAML with empty parameter list."""
        import infra.agent as agent_infra
        import yaml  # type: ignore[import-untyped]

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Call with empty parameters
        agent_infra._generate_metadata_yaml("agent", str(tmp_path), [])

        # Read and parse the generated YAML
        metadata_file = tmp_path / "model-metadata.yaml"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)

        # Verify structure
        assert metadata["name"] == "agent"
        assert metadata["type"] == "inference"
        assert metadata["targetType"] == "agenticworkflow"
        assert metadata["runtimeParameterDefinitions"] == []

    def test_format_and_overwrite(self, tmp_path, monkeypatch):
        """Test _generate_metadata_yaml file formatting and overwrite behavior."""
        import infra.agent as agent_infra
        import yaml  # type: ignore[import-untyped]

        # Mock the application path to point to our tmp_path
        monkeypatch.setattr(agent_infra, "agent_application_path", tmp_path)

        # Create an existing file with different content
        metadata_file = tmp_path / "model-metadata.yaml"
        metadata_file.write_text("old: content\n")

        mock_params = [MagicMock(key="NEW_PARAM", type="string")]
        agent_infra._generate_metadata_yaml("agent", str(tmp_path), mock_params)

        # Check raw file format
        content = metadata_file.read_text()
        assert content.startswith("---\n")
        assert "name: agent" in content
        assert "type: inference" in content
        assert "targetType: agenticworkflow" in content
        assert "runtimeParameterDefinitions:" in content
        assert "fieldName: NEW_PARAM" in content

        # Verify the old file was overwritten
        with open(metadata_file) as f:
            metadata = yaml.safe_load(f)

        assert "old" not in metadata
        assert metadata["name"] == "agent"
        assert metadata["runtimeParameterDefinitions"][0]["fieldName"] == "NEW_PARAM"
