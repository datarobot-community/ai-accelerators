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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom import chat, load_model


@pytest.fixture
def mock_agent():
    with patch("custom.MyAgent") as mock:
        mock_instance = MagicMock()
        mock_instance.invoke = AsyncMock(
            return_value=(
                "agent result",
                [],
                {"completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3},
            )
        )
        mock.return_value = mock_instance
        yield mock, mock_instance


@pytest.fixture
def load_model_result():
    result = load_model("")
    yield result
    thread_pool_executor, event_loop = result
    thread_pool_executor.shutdown(wait=True)


@pytest.fixture
def completion_params():
    return {
        "model": "test-model",
        "messages": [{"role": "user", "content": '{"topic": "test"}'}],
    }


class TestAuthorizationContextPropagation:
    def test_authorization_context_set_in_params(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent
        auth_context = {"token": "test-token", "user_id": "test-user"}

        with patch("custom.resolve_authorization_context", return_value=auth_context):
            chat(completion_params, load_model_result)

        call_kwargs = mock_class.call_args[1]
        assert "authorization_context" in call_kwargs
        assert call_kwargs["authorization_context"] == auth_context

    def test_authorization_context_passed_to_agent(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent
        auth_context = {"token": "test-token", "user_id": "test-user"}

        with patch("custom.resolve_authorization_context", return_value=auth_context):
            chat(completion_params, load_model_result)

        mock_class.assert_called_once()
        call_kwargs = mock_class.call_args[1]
        assert call_kwargs.get("authorization_context") == auth_context

    def test_empty_authorization_context_handled(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent

        with patch("custom.resolve_authorization_context", return_value={}):
            response = chat(completion_params, load_model_result)

        assert response is not None
        mock_instance.invoke.assert_called_once()
        call_kwargs = mock_class.call_args[1]
        assert call_kwargs.get("authorization_context") == {}


class TestHeaderForwarding:
    def test_forwarded_headers_whitelisted(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent
        headers = {
            "x-datarobot-api-key": "secret-key",
            "x-datarobot-api-token": "secret-token",
            "x-custom-header": "should-be-filtered",
        }

        with patch("custom.resolve_authorization_context", return_value={}):
            chat(completion_params, load_model_result, headers=headers)

        call_kwargs = mock_class.call_args[1]
        assert "forwarded_headers" in call_kwargs
        forwarded = call_kwargs["forwarded_headers"]
        assert forwarded["x-datarobot-api-key"] == "secret-key"
        assert forwarded["x-datarobot-api-token"] == "secret-token"
        assert "x-custom-header" not in forwarded

    def test_forwarded_headers_case_insensitive(
        self, mock_agent, load_model_result, completion_params
    ):
        header1 = "X-DataRobot-API-Key"
        header2 = "X-DATAROBOT-API-TOKEN"

        mock_class, mock_instance = mock_agent
        headers = {
            header1: "secret-key",
            header2: "secret-token",
        }

        with patch("custom.resolve_authorization_context", return_value={}):
            chat(completion_params, load_model_result, headers=headers)

        call_kwargs = mock_class.call_args[1]
        forwarded = call_kwargs["forwarded_headers"]
        assert len(forwarded) == 2
        assert header1 in forwarded
        assert header2 in forwarded

    def test_forwarded_headers_empty_when_no_headers(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent

        with patch("custom.resolve_authorization_context", return_value={}):
            chat(completion_params, load_model_result)

        call_kwargs = mock_class.call_args[1]
        assert "forwarded_headers" in call_kwargs
        assert call_kwargs["forwarded_headers"] == {}

    def test_forwarded_headers_empty_when_none(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent

        with patch("custom.resolve_authorization_context", return_value={}):
            chat(completion_params, load_model_result, headers=None)

        call_kwargs = mock_class.call_args[1]
        assert "forwarded_headers" in call_kwargs
        assert call_kwargs["forwarded_headers"] == {}

    def test_only_whitelisted_headers_forwarded(
        self, mock_agent, load_model_result, completion_params
    ):
        mock_class, mock_instance = mock_agent
        headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
            "X-Custom": "value",
        }

        with patch("custom.resolve_authorization_context", return_value={}):
            chat(completion_params, load_model_result, headers=headers)

        call_kwargs = mock_class.call_args[1]
        forwarded = call_kwargs["forwarded_headers"]
        assert len(forwarded) == 0
