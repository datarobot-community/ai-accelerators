import os
import base64
import json

from datarobot_drum import RuntimeParameters
import google.auth
import pandas as pd
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk, CompletionCreateParams
import google.auth.transport.requests
from google.oauth2 import service_account
import requests
from datarobot_drum.drum import description
from time import time

print(f"The DRUM Version is {description.version}")


LOCATION = 'us-central1'
TOKEN_CREATE_TIME = time()

def get_google_credential():
    if os.getenv(
        "DRUM_JAVA_SHARED_JARS"
    ):  # You are running in a custom model environment
        print("Using Custom Model Runtime")
        supplied_credential = RuntimeParameters.get(
            "GOOGLE_APPLICATION_RUNTIME_CREDENTIAL"
        )
        key = supplied_credential["gcpKey"]
        raw_credential, project = google.auth.load_credentials_from_dict(key)
        credential = raw_credential.with_scopes(
            ['https://www.googleapis.com/auth/cloud-platform'])
    else:
        try:
            credential, project = google.auth.default()
            print(f"Using Default Credentials for project {project}")
        except:
            print("last try just look for credential file in directory")
            credential, project = google.auth.load_credentials_from_file(
                "account_key.json"
            )
    return credential, project

def get_token(credential):
    global TOKEN_CREATE_TIME
    TOKEN_CREATE_TIME = time()
    auth_req = google.auth.transport.requests.Request()
    credential.refresh(auth_req)
    return credential.token



def load_model(*args, **kwargs):
    print(f"The DRUM Version is {description.version}")
    credential, project = get_google_credential()
    print(f"Got the Credential for {project}")
    token = get_token(credential)
    client = openai.OpenAI(
    base_url = f'https://{LOCATION}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{LOCATION}/endpoints/openapi',
    api_key = token)
    return credential, client


def score(data, model, **kwargs):
    prompts = data["prompt"].tolist()
    responses = []
    credential, client = model
    if (time() - TOKEN_CREATE_TIME) > 1800:
        token = get_token(credential)
        client.api_key = token
    for p in prompts:
        completion_create_params = {
        "model": "google/gemini-1.5-flash-001",
        "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": p
        }
        ]
    }
        response = client.chat.completions.create(**completion_create_params)
        response_text = response.choices[0].message.content
        responses.append(response_text)

    return pd.DataFrame({"responseText": responses})


def chat(completion_create_params: CompletionCreateParams, model: OpenAI, **kwargs)-> ChatCompletion:
    """Chat Hook compatibale with ChatCompletion
    OpenAI Specification

    Parameters
    ----------
    completion_create_params : CompletionCreateParams
        object that holds all the parameters needed to create the chat completion.
    model : OpenAI
        The model object from openai.  this is injected output from load_model

    Returns
    -------
    ChatCompletion
        the completion object with generated choices. 
    """
    credential, client = model
    if (time() - TOKEN_CREATE_TIME) > 1800:
        token = get_token(credential)
        client.api_key = token
    return client.chat.completions.create(**completion_create_params)

# m = load_model()
# chat({
#     "model": "google/gemini-1.5-flash-001",
#     "messages": [
#       {
#         "role": "system",
#         "content": "You are a helpful assistant."
#       },
#       {
#         "role": "user",
#         "content": "Hello!"
#       }
#     ]
#   }, m)
# score(pd.DataFrame([{'promptText': "Hi who are you"}]), m)