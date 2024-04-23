import base64
import datetime as dt
import json

from helpers import (
    ask_generative_model,
    ask_guard_model,
    DataRobotPredictionError,
    get_custom_metric_id,
    parse_arguments,
    submit_metric,
    write_history,
)
import streamlit as st


def img_to_html(bytes_data):
    img_html = "<img src='data:image/png;base64,{}'/>".format(bytes_data)
    return img_html


def submit_custom_metrics(deployment_id):
    cm_id = get_custom_metric_id(deployment_id)
    submit_metric(deployment_id, dt.datetime.now(), cm_id)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Multimodal Application",
        page_icon="💬",
    )

    args = parse_arguments()
    guard_model_deployment_id = args["guard_model_deployment_id"]
    text_model_deployment_id = args["text_model_deployment_id"]
    multimodal_model_deployment_id = args["multimodal_model_deployment_id"]

    st.title("DataRobot multimodal chat")

    img_file_buffer = st.file_uploader("Upload an image")
    bytes_data = None
    encoded_image = None
    if img_file_buffer is not None:
        bytes_data = img_file_buffer.getvalue()
        st.image(bytes_data)
        encoded_image = base64.b64encode(bytes_data).decode("utf-8")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("Please type in you question here?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message in chat message container
        with st.chat_message("user"):
            if img_file_buffer is not None:
                st.markdown(prompt)
                st.markdown(img_to_html(encoded_image), unsafe_allow_html=True)
            else:
                st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant", avatar="datarobot_logo_icon.png"):
            message_placeholder = st.empty()
            toxic_label, toxic_value = ask_guard_model(guard_model_deployment_id, prompt)

            if toxic_value < 0.5:
                if (prompt is not None) & (img_file_buffer is not None):
                    assistant_response = ask_generative_model(
                        multimodal_model_deployment_id, prompt + "---" + encoded_image
                    )
                else:
                    assistant_response = ask_generative_model(text_model_deployment_id, prompt)
            else:
                if (prompt is not None) & (img_file_buffer is not None):
                    submit_custom_metrics(multimodal_model_deployment_id)
                else:
                    submit_custom_metrics(text_model_deployment_id)
                assistant_response = "Probably we could have a chat on this topic but looks like such questions are not allowed!"

            if encoded_image is not None:
                write_history(
                    dt.datetime.now(),
                    prompt,
                    assistant_response,
                    toxic_value > 0.5,
                    "data:image/png;base64," + encoded_image,
                )
            else:
                write_history(dt.datetime.now(), prompt, assistant_response, toxic_value > 0.5, "")

            message_placeholder.markdown(assistant_response)

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
