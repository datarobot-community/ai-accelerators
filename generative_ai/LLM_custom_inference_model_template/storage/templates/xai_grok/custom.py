from datarobot_drum import RuntimeParameters
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk, CompletionCreateParams
import pandas as pd
import os
from typing import Iterator


def load_model(*args, **kwargs)-> OpenAI:
    if (env_key := os.getenv("xai_grok_api_key")):
        open_api_key = env_key
    else:
        open_api_key = RuntimeParameters.get("xai_grok_api_key")["apiToken"]
    return OpenAI(api_key=open_api_key, base_url="https://api.x.ai/v1")


def score(data: pd.DataFrame, model, **kwargs):
    """This is the legacy score hook for 
    datarobot version prior to 10.2

    Parameters
    ----------
    data : pd.DataFrame
        Input data. the prompt will be taken from 
        the column "promptText" which must exists
    model : OpenAi
        The model object from openai. 

    Returns
    -------
    _type_
        _description_
    """
    prompts = data["promptText"].tolist()
    responses = []

    for prompt in prompts:
        response = model.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": f"{prompt}"},
            ],
            temperature=0,
        )
        responses.append(response.choices[0].message.content)

    return pd.DataFrame({"resultText": responses})

def chat(completion_create_params: CompletionCreateParams, model: OpenAI)-> ChatCompletion | Iterator[ChatCompletionChunk]:
    """Chat Hook compatibale with ChatCompletion
    OpenAI Specification

    Parameters
    ----------
    completion_create_params : CompletionCreateParams
        object that holds all the parameters needed to create the chat completion.
    model : OpenAI
        The model object from openai.  this is injected output from load_model

    Returns
    -------
    ChatCompletion
        the completion object with generated choices. 
    """
    return model.chat.completions.create(**completion_create_params)