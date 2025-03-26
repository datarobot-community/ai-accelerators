import argparse
import base64
from io import BytesIO

from PIL import Image
import cv2 as cv
import requests
import streamlit as st


def get_image_as_b64(image, image_quality):
    if image.size != (224, 224):
        image = image.resize((224, 224))
    image_bytes = image_to_bytes(image, image_quality)
    image_b64 = base64.b64encode(image_bytes).decode("utf8")
    return image_b64


def image_to_bytes(image, image_quality):
    save_args = {}
    target_format = "JPEG"
    save_args["progressive"] = True
    save_args["optimize"] = True
    save_args["quality"] = image_quality
    final_bytes = BytesIO()
    image.save(final_bytes, format=target_format, **save_args)
    return final_bytes.getvalue()


def prepare_data_for_prediction(image_b64):
    body = f"image\n{image_b64}"
    return body


def make_datarobot_deployment_predictions(image_b64, deployment_id):
    data = prepare_data_for_prediction(image_b64)
    API_URL = st.secrets["API_URL"]

    headers = {
        "Content-Type": "text/plain; charset=UTF-8",
        "Authorization": "Bearer {}".format(st.secrets["API_TOKEN"]),
        "DataRobot-Key": st.secrets["DR_KEY"],
    }

    url = API_URL.format(deployment_id=deployment_id)

    predictions_response = requests.post(
        url,
        data=data,
        headers=headers,
    )
    predictions_response.raise_for_status()
    return predictions_response.json()


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="This is a DataRobot Glasses Detection Application"
    )
    parser.add_argument("--deployment_id", action="store", default=[], help="Add the deployment ID")
    args = parser.parse_args()

    return {
        "deployment_id": args.deployment_id,
    }


def main():
    deployment_id = parse_arguments()["deployment_id"]

    st.set_page_config(page_title="DataRobot Glasses Detection App")
    st.title("DataRobot Glasses Detection App 👓")
    st.write("Predicted by DataRobot")

    frame_placeholder = st.empty()
    pred_placeholder = st.empty()
    bar_placeholder = st.empty()
    stop = st.button("Stop")

    cap = cv.VideoCapture(0)
    while cap.isOpened() and not stop:
        ret, frame = cap.read()
        if not ret:
            st.write("Video has been stopped.")
            break
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        frame_placeholder.image(frame, channels="RGB")

        prediction = make_datarobot_deployment_predictions(
            get_image_as_b64(Image.fromarray(frame), 80), deployment_id
        )
        pred = prediction["data"][0]["prediction"]
        pred_placeholder.text("Predicted class: " + pred)

        prediction_values = prediction["data"][0]["predictionValues"]
        value_glasses = prediction_values[1]["value"]
        progress_text = f"Glasses: probability = {round(value_glasses * 100, 2)} %"
        bar_placeholder.progress(value_glasses, text=progress_text)

        if cv.waitKey(1) == ord("q") or stop:
            break
    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()
