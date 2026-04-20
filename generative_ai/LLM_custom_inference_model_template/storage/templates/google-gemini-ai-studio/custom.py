import os
from typing import Any, Iterator, Union

from datarobot_drum import RuntimeParameters
from litellm import completion
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    CompletionCreateParams,
)
import pandas as pd

def load_model(*args, **kwargs):
    if env_key := os.getenv("GEMINI_API_KEY"):
        api_key = env_key
    else:
        api_key = RuntimeParameters.get("GEMINI_API_KEY")["apiToken"]
        os.environ["GEMINI_API_KEY"] = api_key
    return "done"

def load_model(*args, **kwargs):
    if env_key := os.getenv("GEMINI_API_KEY"):
        api_key = env_key
    else:
        api_key = RuntimeParameters.get("GEMINI_API_KEY")["apiToken"]
        os.environ["GEMINI_API_KEY"] = api_key
    return "done"

def score(data: pd.DataFrame, model: str, **kwargs: Any) -> pd.DataFrame:
    prompts = data["promptText"].tolist()
    responses = []

    for p in prompts:
        completion_create_params = {
            "model": "gemini/gemini-2.5-pro-exp-03-25",
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
