from datetime import datetime
import os

import datarobot as dr
from datarobot.mlops.connected.client import MLOpsClient
from datarobotx.common.config import context
import nltk
import pandas as pd
from readability import Readability
import requests
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

nltk.download("punkt")

model = AutoModelForSequenceClassification.from_pretrained("unitary/toxic-bert")
tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert")
toxicity_check = pipeline(
    "text-classification",
    model=model,
    tokenizer=tokenizer,
)

service_url = context.endpoint.split("/api")[0]
mlops_client = MLOpsClient(service_url=service_url, api_key=context.token, verify=True)

CM_API_URL = "https://app.datarobot.com/api/v2/deployments/{}/customMetrics/{}/fromJSON/"
CM_API_KEY = context.token  # os.environ['DR_API_TOKEN']
CM_HEADERS = {
    "Authorization": "Bearer {}".format(CM_API_KEY),
    "User-Agent": "IntegrationSnippet-Requests",
}


def create_external_llm_deployment(name="External Deployment"):
    """Create a DataRobot Model Package, Deployment to monitor External models"""
    pred_env = {
        "name": name + " Environment",
        "description": name + " Environment",
        "platform": "other",
        "supportedModelFormats": ["externalModel"],
    }
    pred_env_id = mlops_client.create_prediction_environment(pred_env)

    model_pkg_name = name + " package"
    model_pkg = {
        "name": model_pkg_name,
        "modelDescription": {
            "modelName": model_pkg_name,
            "description": f"{model_pkg_name} - created via drx",
        },
        "target": {"type": "TextGeneration", "name": "answer"},
    }
    model_pkg_id = mlops_client.create_model_package(model_pkg)

    deployment_id = mlops_client.deploy_model_package(
        model_pkg_id,
        f"{model_pkg_name} Deployment",
        prediction_environment_id=pred_env_id,
    )

    mlops_client.update_deployment_settings(deployment_id, target_drift=False, feature_drift=True)
    model_id = mlops_client.get_deployment(deployment_id)["model"]["id"]

    dr.Deployment.get(deployment_id).update_predictions_data_collection_settings(enabled=True)
    return deployment_id, model_id


def get_text_texicity(text):
    """Calculate toxicity score for text"""
    return toxicity_check(text)[0]["score"]


def get_flesch_score(text):
    """Calculate Flesch readability score for text"""
    readability = Readability(text)
    return readability.flesch().score


def create_custom_metric(
    deployment_id, name, baseline, directionality="lowerIsBetter", type="average"
):
    """Add custom metric to an existing DataRobot deployment"""
    definition = {
        "name": name,
        "description": name,
        "directionality": directionality,
        "units": "num_of_triggers",
        "type": type,
        "baselineValues": [{"value": baseline}],
        "timestamp": {
            "columnName": "timestamp",
            "timeFormat": "%Y-%m-%d %H:%M:%S.%f",
        },
        "value": {"columnName": "value"},
        "isModelSpecific": False,
    }
    metric_id = mlops_client.create_custom_metric(deployment_id, definition)
    dr.Deployment.get(deployment_id).update_predictions_data_collection_settings(enabled=True)
    return metric_id


def submit_custom_metric(deployment_id, custom_metric_id, metric):
    """Record values for an existing custom metric on a deployment"""
    time_ = datetime.today().strftime("%m/%d/%Y %I:%M %p")
    rows = [
        {"timestamp": ts.isoformat(), "value": value}
        for ts, value in zip([pd.to_datetime(time_)], [metric])
    ]
    response = requests.post(
        CM_API_URL.format(deployment_id, custom_metric_id),
        json={
            "modelPackageId": None,
            "buckets": rows,
        },
        headers=CM_HEADERS,
    )
    response.raise_for_status()
