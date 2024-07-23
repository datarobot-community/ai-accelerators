import datetime
import io
from io import StringIO
import os
import pickle
import subprocess
import sys
import time
import warnings

from PIL import Image
import datarobot as dr
from datarobot import Project
import numpy as np
import optuna
import pandas as pd
from pandas import json_normalize
import plotly
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

warnings.filterwarnings("ignore")

with open("credentials.pickle", mode="br") as fi:
    credentials = pickle.load(fi)
API_URL = credentials[0]
DATAROBOT_API_TOKEN = credentials[1]
DATAROBOT_KEY = credentials[2]

MAX_PREDICTION_FILE_SIZE_BYTES = 52428800
MAX_WAIT = 60 * 60


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def make_datarobot_deployment_predictions(data, deployment_id):
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        "Content-Type": "text/plain; charset=UTF-8",
        "Authorization": "Bearer {}".format(DATAROBOT_API_TOKEN),
        "DataRobot-Key": DATAROBOT_KEY,
    }

    url = API_URL.format(deployment_id=deployment_id)
    # Make API request for predictions
    predictions_response = requests.post(
        url,
        data=data,
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


def get_prediction(df, DEPLOYMENT_ID):
    buffer = io.BytesIO()
    wrapper = io.TextIOWrapper(buffer, encoding="utf-8", write_through=True)
    df.to_csv(wrapper)

    predictions_response = make_datarobot_deployment_predictions(
        buffer.getvalue(), DEPLOYMENT_ID
    )

    if predictions_response.status_code != 200:
        try:
            message = predictions_response.json().get(
                "message", predictions_response.text
            )
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


def save_target_deployment_id(target_names, deployment_ids, directions):
    df = pd.DataFrame(
        {
            "Target Name": target_names,
            "Deployment ID": deployment_ids,
            "Optimization Direction": directions,
        }
    )
    df.to_csv("config.csv", index=False)

    return df


def run_optimization(
    trials_num,
    df_feature,
    targets,
    deploy_ids,
    directions,
    feats_name,
    feats_value_min,
    feats_value_max,
):
    def objective(trial):
        df_target = pd.DataFrame(index=[0], columns=feats_name)
        for i, col in enumerate(feats_name):
            low = feats_value_min[i]
            high = feats_value_max[i]
            df_target[col] = trial.suggest_float(col, low, high, step=0.01)

        if len(deploy_ids) == 2:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            return pred1, pred2

        if len(deploy_ids) == 3:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            return pred1, pred2, pred3

        if len(deploy_ids) == 4:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            return pred1, pred2, pred3, pred4

        if len(deploy_ids) == 5:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            return pred1, pred2, pred3, pred4, pred5

        if len(deploy_ids) == 6:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            return pred1, pred2, pred3, pred4, pred5, pred6

        if len(deploy_ids) == 7:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            return pred1, pred2, pred3, pred4, pred5, pred6, pred7

        if len(deploy_ids) == 8:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            return pred1, pred2, pred3, pred4, pred5, pred6, pred7, pred8

        if len(deploy_ids) == 9:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            return pred1, pred2, pred3, pred4, pred5, pred6, pred7, pred8, pred9

        if len(deploy_ids) == 10:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            return pred1, pred2, pred3, pred4, pred5, pred6, pred7, pred8, pred9, pred10

        if len(deploy_ids) == 11:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
            )

        if len(deploy_ids) == 12:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
            )

        if len(deploy_ids) == 13:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
            )

        if len(deploy_ids) == 14:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
            )

        if len(deploy_ids) == 15:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
            )

        if len(deploy_ids) == 16:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
            )
        if len(deploy_ids) == 17:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
            )

        if len(deploy_ids) == 18:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
            )

        if len(deploy_ids) == 19:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
            )

        if len(deploy_ids) == 20:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
            )

        if len(deploy_ids) == 21:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
            )

        if len(deploy_ids) == 22:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
            )

        if len(deploy_ids) == 23:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
            )

        if len(deploy_ids) == 24:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
            )

        if len(deploy_ids) == 25:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
            )

        if len(deploy_ids) == 26:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            pred26 = get_prediction(df_target, deploy_ids[25])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
                pred26,
            )

        if len(deploy_ids) == 27:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            pred26 = get_prediction(df_target, deploy_ids[25])
            pred27 = get_prediction(df_target, deploy_ids[26])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
                pred26,
                pred27,
            )

        if len(deploy_ids) == 28:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            pred26 = get_prediction(df_target, deploy_ids[25])
            pred27 = get_prediction(df_target, deploy_ids[26])
            pred28 = get_prediction(df_target, deploy_ids[27])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
                pred26,
                pred27,
                pred28,
            )

        if len(deploy_ids) == 29:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            pred26 = get_prediction(df_target, deploy_ids[25])
            pred27 = get_prediction(df_target, deploy_ids[26])
            pred28 = get_prediction(df_target, deploy_ids[27])
            pred29 = get_prediction(df_target, deploy_ids[28])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
                pred26,
                pred27,
                pred28,
                pred29,
            )

        if len(deploy_ids) == 30:
            pred1 = get_prediction(df_target, deploy_ids[0])
            pred2 = get_prediction(df_target, deploy_ids[1])
            pred3 = get_prediction(df_target, deploy_ids[2])
            pred4 = get_prediction(df_target, deploy_ids[3])
            pred5 = get_prediction(df_target, deploy_ids[4])
            pred6 = get_prediction(df_target, deploy_ids[5])
            pred7 = get_prediction(df_target, deploy_ids[6])
            pred8 = get_prediction(df_target, deploy_ids[7])
            pred9 = get_prediction(df_target, deploy_ids[8])
            pred10 = get_prediction(df_target, deploy_ids[9])
            pred11 = get_prediction(df_target, deploy_ids[10])
            pred12 = get_prediction(df_target, deploy_ids[11])
            pred13 = get_prediction(df_target, deploy_ids[12])
            pred14 = get_prediction(df_target, deploy_ids[13])
            pred15 = get_prediction(df_target, deploy_ids[14])
            pred16 = get_prediction(df_target, deploy_ids[15])
            pred17 = get_prediction(df_target, deploy_ids[16])
            pred18 = get_prediction(df_target, deploy_ids[17])
            pred19 = get_prediction(df_target, deploy_ids[18])
            pred20 = get_prediction(df_target, deploy_ids[19])
            pred21 = get_prediction(df_target, deploy_ids[20])
            pred22 = get_prediction(df_target, deploy_ids[21])
            pred23 = get_prediction(df_target, deploy_ids[22])
            pred24 = get_prediction(df_target, deploy_ids[23])
            pred25 = get_prediction(df_target, deploy_ids[24])
            pred26 = get_prediction(df_target, deploy_ids[25])
            pred27 = get_prediction(df_target, deploy_ids[26])
            pred28 = get_prediction(df_target, deploy_ids[27])
            pred29 = get_prediction(df_target, deploy_ids[28])
            pred30 = get_prediction(df_target, deploy_ids[29])
            return (
                pred1,
                pred2,
                pred3,
                pred4,
                pred5,
                pred6,
                pred7,
                pred8,
                pred9,
                pred10,
                pred11,
                pred12,
                pred13,
                pred14,
                pred15,
                pred16,
                pred17,
                pred18,
                pred19,
                pred20,
                pred21,
                pred22,
                pred23,
                pred24,
                pred25,
                pred26,
                pred27,
                pred28,
                pred29,
                pred30,
            )

    study = optuna.create_study(directions=directions)
    study.optimize(objective, n_trials=trials_num, timeout=300, gc_after_trial=True)

    trial_all = []
    trial_params = []
    for trial in study.get_trials():
        trial_params.append(trial.params)
        trial_all.append(
            [trial.number, trial.values[0], trial.values[1], trial.values[2]]
        )
    trial_all = pd.DataFrame(trial_all, columns=["Iteration"] + targets)
    trial_params = pd.DataFrame.from_dict(trial_params)
    trial_all = pd.concat([trial_all, trial_params], axis=1)

    trial_pareto = []
    for trial in study.best_trials:
        trial_pareto.append(
            [trial.number, trial.values[0], trial.values[1], trial.values[2]]
        )
    trial_pareto = pd.DataFrame(trial_pareto, columns=["Iteration"] + targets)

    return trial_all, trial_pareto


# ======================================== Start Streamlit ========================================#
st.title("Multi Objective Optimization App")

# ======================================== image ========================================#
# image
dr = Image.open("dr.png")
st.image(dr)

# ======================================== tabs ========================================#
tab1, tab2 = st.tabs(["Simulation", "Visualization"])

with tab1:
    if os.path.isfile("config.csv"):
        config = pd.read_csv("config.csv")
        df_feature = pd.read_csv("feature.csv")
        targets = config["Target Name"].to_list()
        deploy_ids = config["Deployment ID"].to_list()
        ids = ["ID"]
        directions = config["Optimization Direction"].to_list()
        cols = df_feature.columns.to_list()
        feats = [f for f in cols if f not in targets if f not in ids]

        feats_name = st.multiselect(
            "Select features to be simulated", feats, feats, key=1002
        )

        st.markdown(
            "<h1 style='text-align: center; color: grey;'>Simulated Features</h1>",
            unsafe_allow_html=True,
        )
        feats_value_min = []
        feats_value_max = []
        for i in range(len(feats_name)):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader(feats_name[i])
            with col2:
                feat_value_min = st.number_input(
                    "min",
                    step=0.01,
                    format="%0.2f",
                    value=df_feature[feats_name[i]].values.min(),
                    key=i + 400,
                )
                feats_value_min.append(feat_value_min)
            with col3:
                feat_value_max = st.number_input(
                    "max",
                    step=0.01,
                    format="%0.2f",
                    value=df_feature[feats_name[i]].values.max(),
                    key=i + 500,
                )
                feats_value_max.append(feat_value_max)

        st.markdown(
            "<h1 style='text-align: center; color: grey;'>Dropped Features</h1>",
            unsafe_allow_html=True,
        )

        feats_dropped = [f for f in feats if f not in feats_name]
        feats_value_mean = []
        for i in range(len(feats_dropped)):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.subheader(feats_dropped[i])
            with col2:
                feat_value_mean = st.number_input(
                    "mean",
                    step=0.01,
                    format="%0.2f",
                    value=df_feature[feats_dropped[i]].values.mean(),
                    key=i + 600,
                )
                feats_value_mean.append(feat_value_mean)

        st.markdown(
            "<h1 style='text-align: center; color: grey;'>Run Simulation</h1>",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)

        with col2:
            trials_num = st.number_input(
                "Trials Number", step=10, format="%d", value=100, key=10002
            )
            #         with col3:
            if st.button("Simulation Start!", key=10003):
                trial_all, trial_pareto = run_optimization(
                    trials_num,
                    df_feature,
                    targets,
                    deploy_ids,
                    directions,
                    feats_name + feats_dropped,
                    feats_value_min + feats_value_mean,
                    feats_value_max + feats_value_mean,
                )
                trial_pareto["best_trial"] = 1
                trial_all = trial_all.merge(
                    trial_pareto[["Iteration", "best_trial"]],
                    on=["Iteration"],
                    how="left",
                )
                trial_all = trial_all.fillna(0)
                trial_all.to_csv("trial_all.csv", index=False)
                trial_pareto.to_csv("trial_pareto.csv", index=False)
                st.write("Simulation Finished!")

with tab2:
    if os.path.isfile("trial_all.csv"):
        trial_all = pd.read_csv("trial_all.csv")
        trial_pareto = pd.read_csv("trial_pareto.csv").sort_values(targets[0])

        for t in targets:
            fig = px.scatter(
                trial_all,
                x="Iteration",
                y=t,
            )
            fig.update_layout(
                title=t + "Scatter Plot",
                xaxis_title="Iteration",
                yaxis_title=t,
            )
            st.plotly_chart(fig, use_container_width=True)

        # 2d
        target_name = st.multiselect(
            "Select Two Targets", targets, targets[:2], key=1003
        )
        if len(target_name) != 2:
            print("Please select two targets!")
        else:
            trial_pareto = pd.read_csv("trial_pareto.csv").sort_values(target_name[0])
            fig1 = px.line(trial_pareto, x=target_name[0], y=target_name[1])
            fig1.update_traces(line=dict(color="red"))

            fig2 = px.scatter(trial_all, x=target_name[0], y=target_name[1])

            fig = go.Figure(data=fig1.data + fig2.data)
            fig.update_layout(
                title="Pareto Curve(2D)",
                xaxis_title=target_name[0],
                yaxis_title=target_name[1],
            )
            st.plotly_chart(fig, use_container_width=True)

        # 3d
        target_name = st.multiselect("Select Three Targets", targets, targets, key=1004)
        if len(target_name) != 3:
            print("Please select three targets!")
        else:
            fig1 = px.line_3d(trial_pareto, x=targets[0], y=targets[1], z=targets[2])
            fig1.update_traces(line=dict(color="red"))
            fig2 = px.scatter_3d(trial_all, x=targets[0], y=targets[1], z=targets[2])

            fig = go.Figure(data=fig1.data + fig2.data)
            fig.update_layout(
                title="Pareto Curve(3D)",
                scene=dict(
                    xaxis_title=target_name[0],
                    yaxis_title=target_name[1],
                    zaxis_title=target_name[2],
                ),
            )

            st.plotly_chart(fig, use_container_width=True)

        trial_all_sort = trial_all.sort_values(
            ["best_trial"], ascending=False
        ).reset_index(drop=True)
        st.write(trial_all_sort)
        data_as_csv = trial_all_sort.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download data as CSV",
            data_as_csv,
            "benchmark-tools.csv",
            "text/csv",
            key="download-tools-csv",
        )
