from datarobot_drum import RuntimeParameters
from openai import OpenAI
import pandas as pd


def load_model(*args, **kwargs):
    open_api_key = RuntimeParameters.get("openai_api_key")["apiToken"]
    return OpenAI(api_key=open_api_key)


def score(data, model, **kwargs):
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
