#
#  Copyright 2023 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#
import datetime
import json
import os
import time
from urllib.parse import urlparse

from datarobot import Client, Dataset
from datarobot.client import set_client
from generator import *
import pandas as pd
import streamlit as st

print("\ndata synth\n", st.session_state)

st.set_page_config(
    page_title="DataRobot DataSynth",
    page_icon="🤖",
)


def load_data():
    df = pd.DataFrame(
        [
            {"name": "id", "datatype": "id", "options": '{"start_value": 0, "increment": 1}'},
            {"name": "test_bool", "datatype": "bool", "options": "{}"},
            {
                "name": "test_int",
                "datatype": "int",
                "options": '{"min_value": -999, "max_value": 999}',
            },
            {
                "name": "test_int_with_null",
                "datatype": "int",
                "options": '{"min_value": 0, "max_value": 1000000, "null_probability": 0.1}',
            },
            {
                "name": "test_float",
                "datatype": "float",
                "options": '{"min_value": -100.0, "max_value": 100.0}',
            },
            {
                "name": "test_str",
                "datatype": "str",
                "options": '{"length": 10, "null_probability": 0.1}',
            },
            {
                "name": "test_list",
                "datatype": "list",
                "options": '{"values": ["this", "is", "a", "test", "set", "of", "words"], "null_probability": 0.1}',
            },
            {"name": "test_word", "datatype": "word", "options": '{"null_probability": 0.1}'},
            {
                "name": "test_text",
                "datatype": "text",
                "options": '{"length": 50, "null_probability": 0.1}',
            },
            {
                "name": "test_date",
                "datatype": "date",
                "options": '{"start_date": "-10y", "end_date": "today"}',
            },
            {"name": "test_name", "datatype": "name", "options": "{}"},
            {
                "name": "test_list2",
                "datatype": "list",
                "options": '{"values": ["good", "evil"], "weights": [90, 10]}',
            },
            {"name": "test_uuid", "datatype": "uuid", "options": "{}"},
        ]
    )
    return df


def build_generators(df):
    generators = []
    # st.json(df.to_dict(orient='records'))
    for g in df.to_dict(orient="records"):
        # c3.json(g)
        generators.append(
            Generator(name=g["name"], datatype=g["datatype"], **json.loads(g["options"]))
        )
    return generators


def build_dataset(generators_config_df, rows_required):
    st.toast("Building Dataset - Running", icon="💪")
    generators = build_generators(generators_config_df)
    st.session_state["GeneratorsConfig"] = generators_config_df
    st.session_state["Result"] = pd.DataFrame.from_dict(
        generate_rows(generators, rows_required, None)
    )
    st.toast("Building Dataset - Complete", icon="👌")


def reset_settings():
    for item in st.session_state:
        if item not in ["datarobot_endpoint, datarobot_client, datarobot_token"]:
            del st.session_state[item]


def _make_dataset_link(dataset):
    dataset_url = (
        urlparse(st.session_state.DataRobotAPIEndpoint)
        ._replace(path=f"ai-catalog/{dataset.id}")
        .geturl()
    )
    return f"[{dataset.name}]({dataset_url})"


def upload_to_datarobot():
    st.toast("DataRobot Dataset Import - Running", icon="💪")
    fname = st.session_state.DataRobotDatasetName
    set_client(st.session_state.DataRobotClient)
    with st.spinner("DataRobot Dataset Import"):
        st.session_state["DataRobotDataset"] = Dataset.create_from_in_memory_data(
            data_frame=st.session_state["Result"], fname=fname
        )
    st.toast("DataRobot Dataset Import - Complete", icon="👌")


def test_datarobot_connection():
    try:
        st.toast("datarobot connection", icon="🤔")
        st.session_state.DataRobotClient = Client(
            endpoint=st.session_state.DataRobotAPIEndpoint, token=st.session_state.DataRobotAPIToken
        )
        st.toast("datarobot connection", icon="👍")
    except Exception as e:
        st.error(str(e))
        st.session_state.DataRobotClient = None
        st.toast("datarobot connection", icon="👎")


if "GeneratorsConfig" not in st.session_state:
    st.session_state["GeneratorsConfig"] = load_data()

print(st.session_state)

st.title("DataRobot DataSynth")
st.text("Synthetic data generator")

with st.expander("Configuration", expanded=True):
    st.write("### Configuration")
    st.markdown(
        "*Note: the generators config at this time has no 'validation', it will work or fail.  The default table shows most of the options available for all the datatypes, use these as information to get your generators configuration correct*"
    )
    st.write("Column Generators")
    generators_df = st.data_editor(
        st.session_state["GeneratorsConfig"], num_rows="dynamic", use_container_width=True
    )
    st.number_input(
        "Rows Required",
        key="RowsRequired",
        min_value=100,
        max_value=1000000,
        value=st.session_state["RowsRequired"] if "RowsRequired" in st.session_state else 1000,
        step=100,
        disabled=True if "Result" in st.session_state else False,
    )
    st.button(
        "Build Dataset",
        key="BuildDatasetButton",
        use_container_width=True,
        on_click=build_dataset,
        kwargs={
            "generators_config_df": generators_df,
            "rows_required": st.session_state.RowsRequired,
        },
        disabled=True if "Result" in st.session_state else False,
    )

if "Result" in st.session_state:
    with st.expander("Synth Dataset", expanded=True):
        st.write("### Synth Dataset")
        #
        st.write("Generators")
        st.json(generators_df.to_dict(orient="records"), expanded=False)
        #
        st.write("Dataset")
        st.dataframe(st.session_state["Result"], hide_index=True, use_container_width=True)
        #
        summary_df = (
            st.session_state["Result"]
            .describe(include="all")
            .T[["count", "unique", "freq", "min", "mean", "max", "top"]]
        )
        summary_df.fillna("", inplace=True)
        st.write("Dataset Summary")
        st.dataframe(summary_df, use_container_width=True)
        #
        st.session_state.SendToDataRobot = True
else:
    st.session_state.SendToDataRobot = False

if st.session_state.SendToDataRobot == True:
    with st.expander("DataRobot", expanded=True):
        st.write("### DataRobot")
        st.text_input(
            "DataRobot API Endpoint",
            key="DataRobotAPIEndpoint",
            value=os.environ.get("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2"),
        )
        st.text_input("DataRobot API Token", key="DataRobotAPIToken")
        st.button(
            "DataRobot Client Test", on_click=test_datarobot_connection, use_container_width=True
        )
        #
        if "DataRobotClient" in st.session_state and st.session_state.DataRobotClient:
            if "DataRobotDatasetName" not in st.session_state:
                st.session_state.DataRobotDatasetName = (
                    "DataSynth - " + datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                )
            st.text_input("DataRobot Dataset Name", key="DataRobotDatasetName")
            st.button(
                "Import Dataset into DataRobot", key="UploadToDataRobot", use_container_width=True
            )
        if "UploadToDataRobot" in st.session_state and st.session_state.UploadToDataRobot == True:
            upload_to_datarobot()

if "DataRobotDataset" in st.session_state:
    with st.expander("DataRobot DataSet", expanded=True):
        st.write("### DataRobot Dataset")
        dataset = st.session_state.DataRobotDataset
        st.write(f"Id:  {dataset.id}")
        link = _make_dataset_link(st.session_state["DataRobotDataset"])
        st.write(f"Name:  {link}")
