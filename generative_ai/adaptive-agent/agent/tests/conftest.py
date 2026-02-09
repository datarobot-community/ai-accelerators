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
from concurrent.futures import ThreadPoolExecutor

import pytest


@pytest.fixture
def mock_agent_response():
    """
    Fixture to return a mock agent response based on the agent template framework.
    """
    return (
        "agent result",
        [],
        {
            "completion_tokens": 1,
            "prompt_tokens": 2,
            "total_tokens": 3,
        },
    )


@pytest.fixture()
def load_model_result():
    with ThreadPoolExecutor(1) as thread_pool_executor:
        event_loop = asyncio.new_event_loop()
        thread_pool_executor.submit(asyncio.set_event_loop, event_loop).result()
        yield (thread_pool_executor, event_loop)
