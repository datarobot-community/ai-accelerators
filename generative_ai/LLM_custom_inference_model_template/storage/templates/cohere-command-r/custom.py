import cohere
from datarobot_drum import RuntimeParameters
import pandas as pd


def load_model(*args, **kwargs):
    cohere_api_key = RuntimeParameters.get("cohere_api_key")["apiToken"]
    return cohere.Client(cohere_api_key)


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []

    for prompt in prompts:
        response = model.chat(model="command-r", message=prompt)
        responses.append(response.text)

    return pd.DataFrame({"resultText": responses})
