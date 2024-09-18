from anthropic import Anthropic
from anthropic.types import CompletionCreateParams, Message
from datarobot_drum import RuntimeParameters
import pandas as pd
import os
from openai.types.chat import ChatCompletion
from time import time


def load_model(*args, **kwargs):
    if env_key := os.getenv("ANTHROPIC_API_KEY"):
        api_key = env_key
    else:
        api_key = RuntimeParameters.get("ANTHROPIC_API_KEY")["apiToken"]
    return Anthropic(api_key=api_key)


def score(data: pd.DataFrame, model: Anthropic, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []

    for prompt in prompts:
        response = model.messages.create(
            max_tokens=1024,
            temperature=0.5,
            top_p=1.0,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="claude-3-sonnet-20240229",
        )
        responses.append(response.content[0].text)

    return pd.DataFrame({"resultText": responses})


def chat(completion_create_params: CompletionCreateParams, model: Anthropic) -> Message:
    """Chat Hook compatibale with ChatCompletion
    OpenAI Specification

    Parameters
    ----------
    completion_create_params : CompletionCreateParams
        object that holds all the parameters needed to create the chat completion.
    model : Anthropic
        The model object from openai.  this is injected output from load_model

    Returns
    -------
    ChatCompletion
        the completion object with generated choices.
    """
    an_message: Message = model.messages.create(**completion_create_params)
    msg = an_message.content[0]  # TODO: Handle multiple content blocks

    finish_reason = {
        "end_turn": "stop",
        "stop_sequence": "stop",
        "max_tokens": "length",
        "tool_use": "tool_calls",
    }[an_message.stop_reason]

    return ChatCompletion(
        id=an_message.id,
        choices=[
            {
                "message": {"role": an_message.role, "content": msg.text},
                "finish_reason": finish_reason,
                "index": 0,
            }
        ],
        model=str(an_message.model),
        created=int(time()),
        object="chat.completion",
    )
