# Copyright 2024 DataRobot, Inc.
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
from typing import Any, Iterator, Union
from datarobot_drum import RuntimeParameters
import pandas as pd
from litellm import completion
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    CompletionCreateParams,
)


def load_model(*args, **kwargs):
    if env_key := os.getenv("ANTHROPIC_API_KEY"):
        api_key = env_key
    else:
        api_key = RuntimeParameters.get("ANTHROPIC_API_KEY")["apiToken"]
        os.environ["ANTHROPIC_API_KEY"] = api_key
    return "done"


# azure call


def score(data: pd.DataFrame, model: str, **kwargs: Any) -> pd.DataFrame:
    prompts = data["promptText"].tolist()
    responses = []

    for p in prompts:
        completion_create_params = {
            "model": "claude-3-sonnet-20240229",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": p},
            ],
        }
        response = completion(**completion_create_params)
        response_text = response.choices[0].message.content
        responses.append(response_text)

    return pd.DataFrame({"resultText": responses})


def chat(
    completion_params: CompletionCreateParams,
    model: str,
) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
    return completion(**completion_params)
