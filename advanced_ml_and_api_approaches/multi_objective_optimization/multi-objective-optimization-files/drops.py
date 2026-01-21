from concurrent.futures import ThreadPoolExecutor
import json

import datarobot as dr
from pandas import json_normalize
import requests


def get_deployment_info(deployment_id: str, dr_token: str, dr_url: str) -> dict:
    # Get the deployment
    client = dr.Client(token=dr_token, endpoint=dr_url)
    response = client.get("deployments/{}".format(deployment_id))
    if response.status_code != 200:
        raise ValueError(
            "Failed to get deployment info for deployment {}".format(deployment_id)
        )
    deployment = response.json()
    label = deployment["label"]
    model_info = deployment["model"]
    project_id = model_info["projectId"]
    model_id = model_info["id"]
    server_info = deployment.get("defaultPredictionServer")

    # Handle both dedicated prediction server and serverless deployments
    # サーバーレスデプロイメントと専用予測サーバーの両方に対応
    if server_info is not None:
        # Dedicated prediction server
        url = server_info["url"]
        datarobot_key = server_info.get("datarobot-key", "")
    else:
        # Serverless deployment - use API endpoint directly
        # サーバーレスデプロイメント - APIエンドポイントを直接使用
        # Extract base URL from dr_url (e.g., https://app.jp.datarobot.com/api/v2 -> https://app.jp.datarobot.com)
        base_url = dr_url.replace("/api/v2", "")
        url = base_url
        datarobot_key = ""

    return {
        "deployment_id": deployment_id,
        "label": label,
        "project_id": project_id,
        "model_id": model_id,
        "api_url": url,
        "datarobot_key": datarobot_key,
    }


def get_deployment_infos(
    deployment_ids: list[str], dr_token: str, dr_url: str
) -> list[dict]:
    max_workers = max(len(deployment_ids), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        deployments_info = list(
            executor.map(
                lambda deployment_id: get_deployment_info(
                    deployment_id, dr_token, dr_url
                ),
                deployment_ids,
            )
        )
    return deployments_info


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def make_datarobot_deployment_predictions(
    data, deployment_id, dr_token, dr_key, pred_url
):
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {}".format(dr_token),
    }
    # Add DataRobot-Key header only for dedicated prediction server (not serverless)
    # DataRobot-Keyヘッダーは専用予測サーバーの場合のみ追加（サーバーレスでは不要）
    if dr_key:
        headers["DataRobot-Key"] = dr_key

    url = pred_url.format(deployment_id=deployment_id)
    # Make API request for predictions
    predictions_response = requests.post(
        url,
        json=data,
        headers=headers,
    )
    _raise_dataroboterror_for_status(predictions_response)
    # Return a Python dict following the schema in the documentation
    # Return as is
    return predictions_response  # .json()


def _raise_dataroboterror_for_status(response):
    """Raise DataRobotPredictionError if the request fails along with the response returned"""
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        err_msg = "{code} Error: {msg}".format(
            code=response.status_code, msg=response.text
        )
        raise DataRobotPredictionError(err_msg)


def get_prediction(df, deployment_id, dr_token, dr_key, pred_url, max_retries=3):
    records = json.loads(df.to_json(orient="records"))

    for attempt in range(max_retries):
        try:
            predictions_response = make_datarobot_deployment_predictions(
                records, deployment_id, dr_token, dr_key, pred_url
            )

            if predictions_response.status_code == 200:
                pred_values = json_normalize(predictions_response.json()["data"]).prediction.values
                # Return scalar value instead of numpy array for Optuna compatibility
                return float(pred_values[0]) if len(pred_values) == 1 else pred_values

            # Handle non-200 responses
            try:
                message = predictions_response.json().get(
                    "message", predictions_response.text
                )
            except ValueError:
                message = predictions_response.text

            status_code = predictions_response.status_code
            reason = predictions_response.reason

            # Retry on 429 (rate limit) or 5xx errors
            if status_code == 429 or status_code >= 500:
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                    print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {status_code} {reason}")
                    time.sleep(wait_time)
                    continue

            # Raise exception for non-retryable errors or after max retries
            raise DataRobotPredictionError(
                f"Status: {status_code} {reason}. Message: {message}."
            )
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                import time
                wait_time = (attempt + 1) * 2
                print(f"Retry {attempt + 1}/{max_retries} after {wait_time}s: {str(e)}")
                time.sleep(wait_time)
                continue
            raise DataRobotPredictionError(f"Request failed after {max_retries} retries: {str(e)}")


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv("test.env")
    deployment_id = "67990b5ba04ebeb0fbc6403d"
    dr_token = os.getenv("DATAROBOT_API_TOKEN")
    dr_url = os.getenv("DATAROBOT_ENDPOINT")
    print(get_deployment_info(deployment_id, dr_token, dr_url))
