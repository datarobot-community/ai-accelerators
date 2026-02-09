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

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import ANY, AsyncMock, MagicMock, Mock, patch

import pytest


class TestCustomModel:
    def test_load_model(self):
        from custom import load_model

        (thread_pool_executor, event_loop) = load_model("")
        assert isinstance(thread_pool_executor, ThreadPoolExecutor)
        assert isinstance(event_loop, type(asyncio.get_event_loop()))
        thread_pool_executor.shutdown()

    @patch("custom.MyAgent")
    @patch.dict(os.environ, {"LLM_DEPLOYMENT_ID": "TEST_VALUE"}, clear=True)
    @pytest.mark.parametrize("stream", [False, True])
    def test_chat(self, mock_agent, mock_agent_response, stream, load_model_result):
        from custom import chat

        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent_instance.invoke = AsyncMock(return_value=mock_agent_response)
        mock_agent.return_value = mock_agent_instance

        completion_create_params = {
            "model": "test-model",
            "messages": [{"role": "user", "content": '{"topic": "test"}'}],
            "environment_var": True,
            "stream": stream,
        }

        response = chat(completion_create_params, load_model_result=load_model_result)

        # Assert results
        actual = json.loads(response.model_dump_json())
        expected = {
            "id": ANY,
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "logprobs": None,
                    "message": {
                        "content": "agent result",
                        "refusal": None,
                        "role": "assistant",
                        "annotations": None,
                        "audio": None,
                        "function_call": None,
                        "tool_calls": None,
                    },
                }
            ],
            "created": ANY,
            "model": "test-model",
            "object": "chat.completion",
            "service_tier": None,
            "system_fingerprint": None,
            "usage": {
                "completion_tokens": 1,
                "prompt_tokens": 2,
                "total_tokens": 3,
                "completion_tokens_details": None,
                "prompt_tokens_details": None,
            },
            "pipeline_interactions": ANY,
        }
        assert actual == expected

        # Verify mocks were called correctly
        mock_agent.assert_called_once_with(**completion_create_params)
        mock_agent_instance.invoke.assert_called_once_with(
            completion_create_params={
                "model": "test-model",
                "messages": [{"role": "user", "content": '{"topic": "test"}'}],
                "environment_var": True,
                "stream": stream,
                "authorization_context": {},
                "forwarded_headers": {},
            },
        )

    @patch("custom.MyAgent")
    @patch.dict(os.environ, {"LLM_DEPLOYMENT_ID": "TEST_VALUE"}, clear=True)
    def test_chat_streaming(self, mock_agent, load_model_result):
        from custom import chat

        # Create a generator that yields streaming responses
        async def mock_streaming_generator():
            yield (
                "chunk1",
                None,
                {"completion_tokens": 1, "prompt_tokens": 2, "total_tokens": 3},
            )
            yield (
                "chunk2",
                None,
                {"completion_tokens": 2, "prompt_tokens": 2, "total_tokens": 4},
            )
            yield (
                "",
                Mock(model_dump_json=MagicMock(return_value="interactions")),
                {"completion_tokens": 3, "prompt_tokens": 2, "total_tokens": 5},
            )

        # Setup mocks
        mock_agent_instance = MagicMock()
        mock_agent_instance.invoke = AsyncMock(return_value=mock_streaming_generator())
        mock_agent.return_value = mock_agent_instance

        completion_create_params = {
            "model": "test-model",
            "messages": [{"role": "user", "content": '{"topic": "test"}'}],
            "stream": True,
            "environment_var": True,
        }

        response = chat(completion_create_params, load_model_result=load_model_result)

        # Verify response is an iterator
        assert hasattr(response, "__iter__")
        assert hasattr(response, "__next__")

        # Collect all chunks
        chunks = list(response)

        # Should have 3 chunks (2 with content + 1 final)
        assert len(chunks) == 3

        # First chunk with content
        chunk1 = json.loads(chunks[0].model_dump_json())
        assert chunk1["object"] == "chat.completion.chunk"
        assert chunk1["choices"][0]["delta"]["content"] == "chunk1"
        assert chunk1["choices"][0]["finish_reason"] is None
        assert chunk1["model"] == "test-model"

        # Second chunk with content
        chunk2 = json.loads(chunks[1].model_dump_json())
        assert chunk2["choices"][0]["delta"]["content"] == "chunk2"
        assert chunk2["choices"][0]["finish_reason"] is None

        # Final chunk
        final_chunk = json.loads(chunks[2].model_dump_json())
        assert final_chunk["choices"][0]["delta"]["content"] is None
        assert final_chunk["choices"][0]["finish_reason"] == "stop"
        assert final_chunk["pipeline_interactions"] == "interactions"
        assert final_chunk["usage"]["total_tokens"] == 5

        # Verify mocks were called correctly
        mock_agent.assert_called_once_with(**completion_create_params)
        mock_agent_instance.invoke.assert_called_once_with(
            completion_create_params=completion_create_params
        )
