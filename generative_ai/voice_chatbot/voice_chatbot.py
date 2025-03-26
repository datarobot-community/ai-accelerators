import datetime
from io import BytesIO
import json
import sys
import time

import datarobotx as drx
from gtts import gTTS
from gtts.lang import tts_langs
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st
from streamlit_extras.bottom_container import bottom
from streamlit_extras.stylable_container import stylable_container
from streamlit_js_eval import streamlit_js_eval
from streamlit_mic_recorder import mic_recorder, speech_to_text
import streamlit_survey as ss
from textblob import TextBlob

# from streamlit_TTS import auto_play, text_to_speech, text_to_audio
from wordcloud import WordCloud

drx.Context(config_path="drconfig.yaml")
api_ep = drx.Context().endpoint
token = drx.Context().token

# print(f"{api_ep} ++ {token}")

API_URL = "*****"  # noqa
API_KEY = "*****"
DATAROBOT_KEY = "*****"

DRDOC_DEPLOYMENT_ID = "****"
ARTC_DEPLOYMENT_ID = "****"
MOVIE_DEPLOYMENT_ID = "****"
SURVEY_DEPLOYMENT_ID = "****"

DEPLOYMENT_ID = DRDOC_DEPLOYMENT_ID

api_ep = drx.Context().endpoint
token = drx.Context().token

# print(f"{api_ep} ++ {token}")

MAX_PREDICTION_FILE_SIZE_BYTES = 52428800  # 50 MB

rag_deployment = drx.Deployment(DEPLOYMENT_ID)
rag_drkey = token
rag_ep = api_ep


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def make_datarobot_deployment_predictions(
    endpoint,
    data,
    deployment_id,
    token,
    key,
    mimetype="application/json",
    charset="UTF-8",
):
    """
    Make predictions on data provided using DataRobot deployment_id provided.
    See docs for details:
         https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html

    Parameters
    ----------
    data : str
        If using CSV as input:
        Feature1,Feature2
        numeric_value,string

        Or if using JSON as input:
        [{"Feature1":numeric_value,"Feature2":"string"}]

    deployment_id : str
        The ID of the deployment to make predictions with.

    Returns
    -------
    Response schema:
        https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html#response-schema

    Raises
    ------
    DataRobotPredictionError if there are issues getting predictions from DataRobot
    """
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        "Content-Type": "{};charset={}".format(mimetype, charset),
        "Authorization": "Bearer {}".format(API_KEY),
        "DataRobot-Key": DATAROBOT_KEY,
    }

    # url = f"{endpoint}/predApi/v1.0/deployments/{deployment_id}/predictions"
    url = API_URL.format(deployment_id=deployment_id)

    predictions_response = requests.post(
        url,
        data=json.dumps(data),
        headers=headers,
    )

    # print(predictions_response)
    _raise_dataroboterror_for_status(predictions_response)
    # Return a Python dict following the schema in the documentation
    return predictions_response.json()


def _raise_dataroboterror_for_status(response):
    """Raise DataRobotPredictionError if the request fails along with the response returned"""
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        err_msg = "{code} Error: {msg}".format(code=response.status_code, msg=response.text)
        raise DataRobotPredictionError(err_msg)


def make_prediction(prompt) -> dict:
    data = [
        {
            "promptText": prompt,
        }
    ]

    response = make_datarobot_deployment_predictions(rag_ep, data, DEPLOYMENT_ID, token, rag_drkey)

    if (
        (not response)
        or ("error" in response)
        or ("data" in response and "Error" in response["data"][0]["prediction"])
    ):
        raise RuntimeError(f"Exception in Custom Model! {response}")
    print(response)
    report.write(f"lantency = {response['data'][0]['extraModelOutput']['datarobot_latency']}")
    report.write(
        f"token count = {response['data'][0]['extraModelOutput']['datarobot_token_count']}"
    )
    # report.write(response["data"][0]["extraModelOutput"]["datarobot_latency"])
    return response["data"][0]["prediction"]


def stream_data(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)


def ini_chat():
    initial_msg = "How can I help you?"
    if BOT_Selection == "ARTC":
        initial_msg = "Do you want to know more about the event?"
    if BOT_Selection == "DataRobot":
        initial_msg = "Do you have any question to machine learning and AI with DataRobot?"
    if BOT_Selection == "Survey":
        initial_msg = make_prediction(
            "Let's start the survey from the beginneing, one question at one time."
        )
        print("survey initialized")
    st.session_state.messages.clear()
    st.session_state["messages"] = [{"role": "assistant", "content": initial_msg}]


with st.sidebar:
    st.title("Select chatbot 👉")
    BOT_Selection = st.radio(
        "Available bots:",
        key="chat_bot_selection",
        options=[
            "DataRobot",
            "ARTC",
            # "Movies",
            "Survey",
        ],
        captions=[
            "Everything about AutoML and GenAI with DataRobot.",
            "ARTC's running projects.",
            # "Movie storyline database.",
            "Feedback Survey for ARTC event.",
        ],
        # on_change = ini_chat,
    )

    st.button(
        "Start",
        on_click=ini_chat,
    )


match BOT_Selection:
    case "DataRobot":
        DEPLOYMENT_ID = DRDOC_DEPLOYMENT_ID
        # initial_msg = "How can I help you?"
    case "ARTC":
        DEPLOYMENT_ID = ARTC_DEPLOYMENT_ID
        # initial_msg = "How can I help you?"
    case "Movies":
        DEPLOYMENT_ID = MOVIE_DEPLOYMENT_ID
    case "Survey":
        DEPLOYMENT_ID = SURVEY_DEPLOYMENT_ID


chat_tab, wordcloud_tab = st.tabs(["Chatbot", "Analysis"])


with chat_tab:
    chat, report = st.columns([2, 0.3])
    # state = chat.session_state

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "hello"}]
        ini_chat()

    chat_container = chat.container(
        height=streamlit_js_eval(js_expressions="screen.height", key="SCR") - 400
    )

    input_cols = chat.columns([0.1, 0.8, 0.1, 0.1])
    if input_cols[0].button(":broom:"):
        ini_chat()
        # st.session_state.messages.clear()
        # st.session_state["messages"] = [{"role": "assistant", "content": initial_msg}]

    if prompt := input_cols[1].chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        # chat_container.chat_message("user").write(prompt)
        response = make_prediction(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        # chat_container.chat_message("assistant").write(stream_data(response))

    with input_cols[2]:
        voice_text = speech_to_text(
            start_prompt="🎙️",
            stop_prompt="⏹️",
            language="en",
            use_container_width=True,
            just_once=True,
            key="STT",
        )

    if voice_text:
        st.session_state.messages.append({"role": "user", "content": voice_text})
        # chat_container.chat_message("user").write(voice_text)
        response = make_prediction(voice_text)
        st.session_state.messages.append({"role": "assistant", "content": response})
        # chat_container.chat_message("assistant").write(stream_data(response))

    for msg in st.session_state.messages:
        chat_container.chat_message(msg["role"]).write(msg["content"])

    if input_cols[3].button(":loud_sound:"):
        msg = st.session_state.messages[-1]["content"]
        # chat.write(len(msg))
        if len(msg) > 1000:
            msg = "It's too long, and I'm getting tired."
        # audio=text_to_audio(msg,language='en')
        print(msg)
        tts_buffer = gTTS(msg, lang="en", tld="com", slow=False)
        # audio_file = open("temp.mp3", "rb")
        # audio_bytes = audio_file.read()
        mp3_fp = BytesIO()
        tts_buffer.write_to_fp(mp3_fp)
        chat.audio(mp3_fp, format="audio/mp3", start_time=0)

with wordcloud_tab:
    wordcloud_text = " "
    prompt_history = "prompt"
    respond_history = "respond"
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            prompt_history += "  \n  " + msg["content"]
        if msg["role"] == "assistant":
            respond_history += "  \n  " + msg["content"]

    selection, show = st.columns([1, 4])

    with selection:
        wordcloud_options = st.radio(
            "Select what to analyse",
            key="wordcloud_selection",
            options=[
                "Prompts",
                "Responses",
            ],
        )

        match wordcloud_options:
            case "Prompts":
                wordcloud_text = prompt_history
            case "Responses":
                wordcloud_text = respond_history

    # st.write(prompt_history)
    # st.write(respond_history)

    with show:
        wordcloud = WordCloud(width=800, height=400, background_color="white").generate(
            wordcloud_text
        )

        # Plot the word cloud
        st.subheader("Word Cloud")
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        st.pyplot(plt)

        sentiment = TextBlob(wordcloud_text).sentiment
        st.subheader("Sentiment Analysis")
        st.write(f"Polarity: {sentiment.polarity}")
        st.write(f"Subjectivity: {sentiment.subjectivity}")

    # st.write("Survey")
    survey = ss.StreamlitSurvey("ARTC event feedback survey")
    st.title("ARTC event feedback survey")
    st.write("Please take 5 mins to share your feedback to today's event. Thank you!")

    Q1 = survey.radio(
        "Would you comfortable with sharing your responses and data with the AI COE team?",
        options=[
            "Yes",
            "No",
        ],
        index=0,
        horizontal=True,
        id="Q1",
    )
    if Q1 == "Yes":
        Q2 = survey.select_slider(
            "How would you rate your understanding of how AI can be applied in your organisation?",
            options=[
                "New to AI",
                "Exploring.",
                "Piloting",
                "Have use cases",
                "Deploy AI on regular basis",
            ],
            id="Q2",
        )

        Q3 = survey.multiselect(
            id="Q3",
            label="What are some concerns regarding adopting AI solutions in your organisation?",
            options=[
                "High implementation costs.",
                "Lack of skilled workforce.",
                "Data Privacy and Security Issues.",
                "Ethical Concerns.",
                "Resistance to change within the organisation.",
                "Integration with Existing Systems.",
                "Lack of Data/Sensor-isation.",
                "Others (Please specify)",
            ],
        )
        if "Others (Please specify)" in Q3:
            survey.text_input(label="Please specify", id="Q3a")

        Q4 = survey.select_slider(
            id="Q4",
            label="Has your company explored or implemented any AI solutions so far?",
            options=[
                "No, we have not yet considered.",
                "No, but we are considering.",
                "Yes, we are currently exploring.",
                "Yes, we have.",
            ],
        )

        Q5 = survey.select_slider(
            id="Q5",
            label="How willing is your company to invest/invest more in AI technologies withint the next few months?",
            options=[
                "Very unwilling.",
                "Somewhat unwilling.",
                "Neutral.",
                "Somewhat willing.",
                "Very willling.",
            ],
        )

        Q6 = survey.multiselect(
            id="Q6",
            label="What resources or support would you need to feel confident in adopting AI?",
            options=[
                "Training and education for employees.",
                "Clear ROI and business case.",
                "External expertise and consultancy.",
                "Tools and platforms for AI development.",
                "Integration support with existing systems.",
                "Others (Please specify)",
            ],
        )
        if "Others (Please specify)" in Q6:
            survey.text_input(label="Please specify", id="Q6a")

        Q7 = survey.multiselect(
            id="Q7",
            label="Which of the following 5 pain points is most relevant to you?",
            options=[
                "Product/Component/Process Design.",
                "Quality Assurance.",
                "Operations Optimisation.",
                "Industrial Automation.",
                "Predictive Maintenance.",
            ],
        )

        Q8 = survey.radio(
            # id = "Q8",
            label="Did you manage to take part in the AI Experience Centre Tour?",
            options=[
                "Yes",
                "No",
            ],
            index=0,
            horizontal=True,
            id="Q8",
        )

        if Q8 == "Yes":
            Q8a = survey.multiselect(
                id="Q8a",
                label="Which of the AI solutions that were showcased during the AI Experience is most relevant to your needs?",
                options=[
                    "Spend Categorisation through NLP.",
                    "AI Cleansheet.",
                    "Procurement Negotiation Scripting.",
                    "AI_enabled Production Capacity Planning.",
                    "GenAI maintenance chatbot.",
                    "Predictive and Prescriptive Maintenance.",
                    "AI/ML based demand forecasting.",
                    "AA based Supply Chain Planning and S&OP.",
                    "Set point Optimisation.",
                    "Gen-AI logistics for customer service.",
                ],
            )

            Q8b = survey.multiselect(
                id="Q8b",
                label="Which of the following AI solutions is any would you like to start adopting in the next 12 months?",
                options=[
                    "Spend Categorisation through NLP.",
                    "AI Cleansheet.",
                    "Procurement Negotiation Scripting.",
                    "AI_enabled Production Capacity Planning.",
                    "GenAI maintenance chatbot.",
                    "Predictive and Prescriptive Maintenance.",
                    "AI/ML based demand forecasting.",
                    "AA based Supply Chain Planning and S&OP.",
                    "Set point Optimisation.",
                    "Gen-AI logistics for customer service.",
                ],
            )
        json = survey.to_json()
        if st.button("Submit"):
            st.json(json)

    else:
        st.write("Thank You!")
    # print(Q3)
