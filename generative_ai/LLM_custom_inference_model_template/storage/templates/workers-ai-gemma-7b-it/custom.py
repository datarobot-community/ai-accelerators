import logging

from datarobot_drum import RuntimeParameters
import pandas as pd
import requests

logger = logging.getLogger(__name__)

system_prompt = "You are a friendly assistant"


def load_model(*args, **kwargs):
    account_id = RuntimeParameters.get("worker_ai_account_id")
    auth_token = RuntimeParameters.get("worker_ai_auth_token")["apiToken"]
    return {"account_id": account_id, "auth_token": auth_token}


def score(data, model, **kwargs):
    prompts = data["promptText"].tolist()
    account_id = model.get("account_id")
    auth_token = model.get("auth_token")
    responses = []

    for prompt in prompts:
        logger.info(f"prompt: {prompt}")
        response = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@hf/google/gemma-7b-it",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
            },
        )
        result = response.json()
        responses.append(result["result"]["response"])
    return pd.DataFrame({"resultText": responses})
