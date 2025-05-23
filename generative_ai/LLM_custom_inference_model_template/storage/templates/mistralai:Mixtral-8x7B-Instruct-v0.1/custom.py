from datarobot_drum import RuntimeParameters
from openai import OpenAI
import pandas as pd


def load_model(*args, **kwargs):
    api_key = RuntimeParameters.get("togetherai_api_key")["apiToken"]
    client = OpenAI(api_key=api_key, base_url="https://api.together.xyz/v1")
    return client


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []

    for prompt in prompts:
        response = model.chat.completions.create(
            model="mistralai/Mixtral-8x7B-Instruct-v0.1",
            messages=[
                {"role": "user", "content": f"{prompt}"},
            ],
            temperature=0.7,
            top_p=0.7,
            max_tokens=500,
        )
        responses.append(response.choices[0].message.content)

    return pd.DataFrame({"resultText": responses})
