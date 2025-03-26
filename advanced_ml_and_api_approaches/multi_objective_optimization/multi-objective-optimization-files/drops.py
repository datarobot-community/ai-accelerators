import json
from concurrent.futures import ThreadPoolExecutor

import datarobot as dr
import requests
from pandas import json_normalize


def get_deployment_info(deployment_id: str, dr_token: str, dr_url: str) -> dict:
    # Get the deployment
    client = dr.Client(token=dr_token, endpoint=dr_url)
    response = client.get("deployments/{}".format(deployment_id))
    if response.status_code != 200:
        raise ValueError("Failed to get deployment info for deployment {}".format(deployment_id))
    deployment = response.json()
    label = deployment["label"]
    model_info = deployment["model"]
    project_id = model_info["projectId"]
    model_id = model_info["id"]
    server_info = deployment["defaultPredictionServer"]
    url = server_info["url"]
    datarobot_key = server_info["datarobot-key"]

    return {
        "deployment_id": deployment_id,
        "label": label,
        "project_id": project_id,
        "model_id": model_id,
        "api_url": url,
        "datarobot_key": datarobot_key,
    }


def get_deployment_infos(deployment_ids: list[str], dr_token: str, dr_url: str) -> list[dict]:
    max_workers = max(len(deployment_ids), 10)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        deployments_info = list(
            executor.map(
                lambda deployment_id: get_deployment_info(deployment_id, dr_token, dr_url),
                deployment_ids,
            )
        )
    return deployments_info


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def make_datarobot_deployment_predictions(data, deployment_id, dr_token, dr_key, pred_url):
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "Authorization": "Bearer {}".format(dr_token),
        "DataRobot-Key": dr_key,
    }

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
        err_msg = "{code} Error: {msg}".format(code=response.status_code, msg=response.text)
        raise DataRobotPredictionError(err_msg)


def get_prediction(df, deployment_id, dr_token, dr_key, pred_url):
    records = json.loads(df.to_json(orient="records"))
    predictions_response = make_datarobot_deployment_predictions(
        records, deployment_id, dr_token, dr_key, pred_url
    )

    if predictions_response.status_code != 200:
        try:
            message = predictions_response.json().get("message", predictions_response.text)
            status_code = predictions_response.status_code
            reason = predictions_response.reason

            print(
                "Status: {status_code} {reason}. Message: {message}.".format(
                    message=message, status_code=status_code, reason=reason
                )
            )
        except ValueError:
            print("Prediction failed: {}".format(predictions_response.reason))
            predictions_response.raise_for_status()
    else:
        return json_normalize(predictions_response.json()["data"]).prediction.values


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv("test.env")
    deployment_id = "67990b5ba04ebeb0fbc6403d"
    dr_token = os.getenv("DATAROBOT_API_TOKEN")
    dr_url = os.getenv("DATAROBOT_ENDPOINT")
    print(get_deployment_info(deployment_id, dr_token, dr_url))
