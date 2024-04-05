from anthropic import Anthropic
from datarobot_drum import RuntimeParameters
import pandas as pd


def load_model(*args, **kwargs):
    api_key = RuntimeParameters.get("ANTHROPIC_API_KEY")["apiToken"]
    return Anthropic(api_key=api_key)


def score(data, model, **kwargs):
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
            model="claude-3-opus-20240229",
        )
        responses.append(response.content[0].text)

    return pd.DataFrame({"resultText": responses})
