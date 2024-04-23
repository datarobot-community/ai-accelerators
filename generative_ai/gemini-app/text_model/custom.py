import base64
import json

from datarobot_drum import RuntimeParameters
from google.oauth2 import service_account
import pandas as pd
import vertexai
from vertexai.preview import generative_models
from vertexai.preview.generative_models import GenerativeModel


def load_model(*args, **kwargs):
    key = RuntimeParameters.get("google_service_account")["apiToken"]
    json_acct_info = json.loads(base64.b64decode(key))
    credentials = service_account.Credentials.from_service_account_info(json_acct_info)

    vertexai.init(project="YOUR-VERTEXAI-PROJECT", credentials=credentials)
    model = GenerativeModel("gemini-pro")
    return model


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    responses = []
    safety_config = {
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }

    for prompt in prompts:
        response = model.generate_content(
            [prompt],
            generation_config={"max_output_tokens": 2048, "temperature": 0, "top_p": 1},
            stream=False,
            safety_settings=safety_config,
        )
        responses.append(response.text)

    return pd.DataFrame({"resultText": responses})
