#
#  Copyright 2025 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#

import datetime
import json
import os
import re

from bson import ObjectId
import datarobot as dr
from datarobot.models.model_registry import RegisteredModelListFilters
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_timeline import timeline
import yaml

# Grab the DataRobot client that has already been built for us
client = dr.Client()

# Set page layout
st.set_page_config(layout="wide")


# Render styles to the page
def render_css():
    st.markdown(
        f"""
        <style>
            header {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            input[type="date"] {{
                appearance: none; /* Resets default styling */
                -webkit-appearance: none; /* Safari fix */
                -moz-appearance: none; /* Firefox fix */
            }}
            .uc_block {{
                background-color: #333;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                font-family: 'Arial', sans-serif;
                color: #eee;
                box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.1);
                overflow: auto;
                flex: 1;
                vertical-align: middle;
                margin: 0 10px;
            }}
            .block-container {{
                padding-top: 0px !important;
                margin-top: 10px !important;
            }}
            .custom-dropdown {{
                width: 250px;
                padding: 10px;
                font-size: 16px;
                border-radius: 8px;
                border: 2px solid #4CAF50;
                background-color: #bbb;
                color: #333;
                appearance: none; /* Removes default browser styling */
                -webkit-appearance: none;
                -moz-appearance: none;
                cursor: pointer;
                transition: all 0.3s ease-in-out;
            }}
            .custom-dropdown:hover,
            .custom-dropdown:focus {{
                border-color: #45a049;
                box-shadow: 0px 4px 8px rgba(0, 0, 0, 0.2);
            }}
            /* Arrow Indicator */
            .custom-dropdown {{
                background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="%234CAF50"><path d="M5 8l5 5 5-5H5z"/></svg>');
                background-repeat: no-repeat;
                background-position: right 10px center;
                background-size: 16px;
                padding-right: 30px; /* Space for arrow */
            }}
            .custom-dropdown option {{
                background: #bbb;
                color: black;
                font-size: 16px;
            }}
            .custom-input {{
                font-size: 16px;
                border: 2px solid #4CAF50;
                background-color: #bbb;
                color: #333;
                cursor: pointer;
                transition: all 0.3s ease-in-out;
                outline: none;
                flex: 2;
                width: 75%;
                padding: 8px;
                border-radius: 5px;
            }}

            /* Remove default browser styles for date inputs */
            .custom-input::-webkit-calendar-picker-indicator {{
                background: none;
                color: transparent;
                cursor: pointer;
            }}
            /* Custom Calendar Icon */
            .custom-input {{
                background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="%234CAF50"><path d="M6 2a1 1 0 011 1v1h6V3a1 1 0 112 0v1h1a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2h1V3a1 1 0 011-1zM4 8v8h12V8H4z"/></svg>');
                background-repeat: no-repeat;
                background-position: right 10px center;
                background-size: 18px;
                padding-right: 35px; /* Space for calendar icon */
            }}
            .form-container {{
                margin: 20px auto;
                display: flex;
                flex-direction: row;
                gap: 15px;
                align-items: center;
                overflow: auto;
            }}
            .form-group {{
                display: flex;
                align-items: left;
                justify-content: space-between;
            }}
            .form-group label {{
                flex: 1;
                min-width: 150px;
                text-align: right;
                margin-right: 10px;
            }}
            .submit-button {{
                width: 75%;
                padding: 10px;
                font-size: 16px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
            .submit-button:hover {{
                background-color: #45a049;
            }}
            .container {{
                display: flex;
                width: 100%;
            }}
            .box {{
                flex: 1;
                padding: 20px;
                color: white;
                background-color: #333
            }}
            label {{
                display: block;
                font-weight: bold;
                font-size: 14px;
                color: #eee;
                margin-top: 10px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# output a textbox to separate sections of text.
def styled_text_box(text: str, sidebar=False):
    output = f"""
        <div class="uc_block">
            {text}
        </div><br>
        """
    if sidebar:
        st.sidebar.markdown(output, unsafe_allow_html=True)
    else:
        st.markdown(output, unsafe_allow_html=True)


# Find and extract YAML values in a block of input text. This is used to pull the
# target date and status from the use case description. It returns two values:
# the provided text minus the YAML lines, and the YAML lines as a dictionary
def extract_yaml_lines(text: str):
    yaml_lines = []
    plain_lines = []
    y_out = {}

    # Regular expression for YAML-style key-value pairs
    yaml_pattern = re.compile(r"^\s*([a-zA-Z0-9_-]+)\s*:\s*(.+)$")
    if text:
        for line in text.splitlines():
            match = yaml_pattern.match(line)
            if match:
                yaml_lines.append(line)
            else:
                # If this line isn't YAML, keep it in a separate list
                plain_lines.append(line)
    if yaml_lines:
        # Join extracted lines and parse as YAML
        y_out = yaml.safe_load("\n".join(yaml_lines))

    return "\n".join(plain_lines), y_out


# Output a menu card for a use case, with a brief status summary pulled from the description
def render_use_case_header(use_case):
    # Extract YAML values to render project status
    description, metadata = extract_yaml_lines(use_case.description)
    # check for expected YAML values
    if isinstance(metadata, dict) and "target_date" in metadata.keys():
        target_date = metadata.get("target_date", "Undefined ❌")
        status = metadata.get("status", "Undefined ❌")
        if status == "green":
            status += " ✅"
        elif status == "yellow":
            status += " ⚠️"
        else:
            status += " ⛔️"
        description = f"<br><strong>Target Date:</strong> {target_date} <br> <strong>Status:</strong> {status} <br><br>"
    else:
        description = "Project status is undefined"
    # link to drill into the use case
    uc_url = f"?use_case_id={use_case.id}"
    return f'<a href="{uc_url}" target="_self">{use_case.name}</a><br>{description}'


# Grab all the use cases and append them to the list of elements to render in the sidebar
def render_sidebar():
    st.sidebar.image("logo.svg", use_container_width=True)
    st.sidebar.header("Use Cases")
    use_cases = dr.UseCase.list()
    element_list = []
    for use_case in use_cases:
        styled_text_box(render_use_case_header(use_case=use_case), True)


# Update the use case description with new YAML values if status has been modified
def update_use_case_description(use_case_id, new_status=None, new_target=None):
    if new_target == "":
        new_target = None
    # update the description if either status variable has been supplied
    if new_status or new_target:
        uc = dr.UseCase.get(use_case_id)
        meta_out = ""
        # separate the plain text from the YAML, update the YAML dictionary, then recombine and update the use case description
        description, metadata = extract_yaml_lines(uc.description)
        if new_status:
            metadata["status"] = new_status
        if new_target:
            metadata["target_date"] = new_target
        for k, v in metadata.items():
            meta_out += f"{k}: {v}\n"
        uc.update(description=f"{description}\n{meta_out}")


# Load use case details when a user drills in
def render_use_case(use_case_id):
    try:
        uc = dr.UseCase.get(use_case_id)
        st.header(uc.name)
        st.markdown(f"[View use case in DataRobot]({uc.get_uri()})")
    except:
        st.error("An error occurred while loading this use case.")

    # init a bunch of empty variables that we'll append to later
    description = ""
    project_list = ""
    registered_model_list = ""
    deployed_model_list = ""
    dataset_list = ""
    # registered_models = []
    # deployed_models = []
    starred_models = {}

    # grab use case start date and default project length to fill in the timeline in case no target date is defined
    uc_created_date = datetime.datetime.strptime(uc.created_at, "%Y-%m-%d %H:%M:%S.%f")
    default_project_length = os.environ.get("DEFAULT_PROJECT_LENGTH", 90)

    # grab all members of the use case
    mem_list = uc.members + uc.owners
    members = ", ".join([mem.full_name for mem in mem_list])

    # collect associated assets
    projects = uc.list_projects()
    datasets = uc.list_datasets()
    registered_models = client.get(f"useCases/{use_case_id}/registeredModels").json()[
        "data"
    ]
    deployed_models = client.get(f"useCases/{use_case_id}/deployments").json()["data"]
    vector_dbs = client.get(f"useCases/{use_case_id}/vectorDatabases").json()["data"]
    playgrounds = client.get(f"useCases/{use_case_id}/playgrounds").json()["data"]
    apps = client.get(f"useCases/{use_case_id}/applications").json()["data"]

    # render status variables and description
    target_date = "Undefined ❌"
    status = "Undefined ❌"
    description, metadata = extract_yaml_lines(uc.description)
    if isinstance(metadata, dict) and "target_date" in metadata.keys():
        target_date = metadata.get("target_date", "Undefined ❌")
        status = metadata.get("status", "Undefined ❌")
        if status == "green":
            status += " ✅"
        elif status == "yellow":
            status += " ⚠️"
        else:
            status += " ⛔️"
    if len(description) > 0:
        description += "<br><br>"
    description += f"Target Date: {target_date}<br>Status: {status}"

    # render form to set project status vars
    update_html = f"""
        <form method="get" class="form-container">
            <input type="hidden" name="use_case_id" value="{uc.id}">
            <div class="form-group">
                <label for="new_status">New Status:</label>
                <select name="new_status" class="custom-dropdown" id="new_status">
                    <option value="green">green ✅</option>
                    <option value="yellow">yellow ⚠️</option>
                    <option value="red">red ⛔️</option>
                </select>
            </div>
            <div class="form-group">
                <label for="new_target">New Target Date:</label>
                <input type="date" name="new_target" id="new_target" class="custom-input">
            </div>
            <input type="submit" value="Submit Update" class="submit-button">
        </form>
    """
    st.markdown(
        f'<div class="container"><div class="uc_block">{description}</div><div class="uc_block">{update_html}</div></div><br>',
        unsafe_allow_html=True,
    )

    # render list of use case members
    styled_text_box(f"<h2>Members</h2>{members}")

    # build and render the timeline
    if target_date == "Undefined ❌":
        target_date = uc_created_date + datetime.timedelta(days=default_project_length)
    events = {
        "eras": [
            {
                "start_date": {
                    "year": uc_created_date.year,
                    "month": uc_created_date.month,
                    "day": uc_created_date.day,
                },
                "end_date": {
                    "year": target_date.year,
                    "month": target_date.month,
                    "day": target_date.day,
                },
                "text": {
                    "headline": "Project Timeline",
                    "text": "Gathering project assets and approvals.",
                },
            }
        ],
        "groups": [
            {
                "id": 1,
                "content": "Project Setup",
                "style": "color: red; background-color: pink;",
            },
            {
                "id": 2,
                "content": "Model Training and Evaluation",
                "style": "color: yellow; background-color: blue;",
            },
            {
                "id": 3,
                "content": "Model Registration and Approval",
                "style": "color: red; background-color: green;",
            },
            {
                "id": 4,
                "content": "Production Deployment and Maintenance",
                "style": "color: white; background-color: black;",
            },
        ],
        "events": [
            {
                "start_date": {
                    "year": uc_created_date.year,
                    "month": uc_created_date.month,
                    "day": uc_created_date.day,
                },
                "text": {"headline": "Use Case Start", "text": "Use case created"},
                "group": 1,
            }
        ],
    }
    for d in datasets:
        node_date = ObjectId(d.id).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Dataset Registered", "text": d.name},
                "group": 1,
            }
        )
    for v in vector_dbs:
        node_date = ObjectId(v["id"]).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Vector Database Created", "text": v["id"]},
                "group": 1,
            }
        )
    for p in projects:
        # grab and save all the starred models in the project. this will also be used when rendering the project list
        starred_models[p.id] = p.get_models(
            search_params={"is_starred": True}, use_new_models_retrieval=True
        )
        node_date = p.created
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Experiment Started", "text": p.project_name},
                "group": 2,
            }
        )
        for m in starred_models[p.id]:
            node_date = ObjectId(m.id).generation_time
            events["events"].append(
                {
                    "start_date": {
                        "year": node_date.year,
                        "month": node_date.month,
                        "day": node_date.day,
                    },
                    "text": {"headline": "Key Model Trained", "text": m.model_type},
                    "group": 2,
                }
            )
    for p in playgrounds:
        node_date = ObjectId(p["id"]).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {
                    "headline": "Generative AI Playground Created",
                    "text": p["id"],
                },
                "group": 2,
            }
        )
    for m in registered_models:
        node_date = ObjectId(m["id"]).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Model Registered", "text": m["name"]},
                "group": 3,
            }
        )
    for m in deployed_models:
        node_date = ObjectId(m["id"]).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Model Deployed", "text": m["label"]},
                "group": 4,
            }
        )
    for a in apps:
        print(a)
        node_date = ObjectId(a["applicationId"]).generation_time
        events["events"].append(
            {
                "start_date": {
                    "year": node_date.year,
                    "month": node_date.month,
                    "day": node_date.day,
                },
                "text": {"headline": "Application Registered", "text": a["name"]},
                "group": 1,
            }
        )
    st.title("Project Timeline")
    timeline(events, height=380)

    # render list of datasets
    for d in datasets:
        dataset_list += f'<strong>Dataset: <a href="{d.get_uri()}">{d.name}</a><br><br>'
    for v in vector_dbs:
        dataset_list += f"<strong>Vector Database: <a href=\"https://app.datarobot.com/usecases/{uc.id}/vector-databases/{p['id']}\">{p['id']}</a><br>"
    styled_text_box(f"<h2>Setup</h2>{dataset_list}")

    # render list of projects and any starred models they contain
    for p in projects:
        project_list += (
            f'<strong>Experiment: <a href="{p.get_uri()}">{p.project_name}</a><br>'
        )
        if len(starred_models[p.id]) > 0:
            project_list += "<strong>Starred Models: </strong>"
            project_list += ", ".join(
                [
                    f'<a href="{m.get_uri()}">{m.model_type}</a>'
                    for m in starred_models[p.id]
                ]
            )
        project_list += "<br><br>"
    for p in playgrounds:
        project_list += f"<strong>Playground: <a href=\"https://app.datarobot.com/usecases/{uc.id}/playgrounds/{p['id']}/info\">{p['id']}</a><br>"
    styled_text_box(f"<h2>Evaluation</h2>{project_list}")

    # render list of registered models
    if len(registered_models) > 0:
        registered_model_list += "<strong>Registered Models: </strong>"
        registered_model_list += "  \n".join(
            [
                f"<a href=\"https://app.datarobot.com/registry/registered-models/{rm['id']}/\">{rm['name']}</a><br>"
                for rm in registered_models
            ]
        )
    else:
        registered_model_list = (
            "There are no models currently registered from this use case."
        )
    styled_text_box(f"<h2>Approval</h2>{registered_model_list}")

    # render list of deployed models
    if len(deployed_models) > 0:
        deployed_model_list += "<strong>Deployed Models: </strong>"
        deployed_model_list += "  \n".join(
            [
                f"<a href=\"https://app.datarobot.com/console-nextgen/deployments/{d['id']}/overview\">{d['label']}</a>"
                for d in deployed_models
            ]
        )
    else:
        deployed_model_list = (
            "There are no models currently deployed from this use case."
        )
    for a in apps:
        deployed_model_list += f"<br><strong>Application: <a href=\"https://app.datarobot.com/registry/applications/{a['source']}/app-info/{a['applicationId']}\">{a['name']}</a><br>"
    styled_text_box(f"<h2>Production</h2>{deployed_model_list}")


if __name__ == "__main__":
    # look for query params and try to update the use case if needed
    use_case_id = st.query_params.get("use_case_id", None)
    new_status = st.query_params.get("new_status", None)
    new_target = st.query_params.get("new_target", None)
    update_use_case_description(use_case_id, new_status, new_target)

    # clear query parameters to prevent bookmarking a URL with update parameters defined
    st.query_params.clear()

    # render common content
    render_css()
    render_sidebar()

    # drill into a use case if one has been selected from the nav menu
    if use_case_id:
        render_use_case(use_case_id)
    else:
        st.title("DataRobot Use Case Explorer")
        st.markdown(
            "Browse your use cases and review project status. Make a selection from the menu to continue."
        )
        styled_text_box(
            "Target date and status can be set via this app, or by adding the appropriate YAML keys to your use case description, ex:<br><br>target_date: 2025-05-23<br>status: green"
        )
