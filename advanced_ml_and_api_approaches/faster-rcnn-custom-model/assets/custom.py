import base64
from io import BytesIO

from PIL import Image
import cv2
import numpy as np
import pandas as pd
import torch
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
    FasterRCNN_ResNet50_FPN_Weights,
)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor


def load_model(checkpoint_path: str):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = fasterrcnn_resnet50_fpn(pretrained_backbone=False)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=2)
    model.load_state_dict(torch.load("model_state_dict.htp", map_location=device))
    model.to(device)
    return model


def score_unstructured(model, data, query, **kwargs):
    print("Incoming content type params: ", kwargs)
    print("Incoming data type: ", type(data))
    print("Incoming query params: ", query)

    if isinstance(data, bytes):
        data = data.decode("utf8")

    output = do_faster_rcnn_scoring(model, data)

    ret_data = output.to_json()
    ret_kwargs = {"mimetype": "application/json"}
    ret = ret_data, ret_kwargs

    return ret


def split_box(row):
    return pd.Series(row["boxes"])


def do_faster_rcnn_scoring(model, image_b64):
    # Decode the image from the base64 input data
    image_bytes = base64.b64decode(image_b64)
    decoded_image = np.array(Image.open(BytesIO(image_bytes)))

    results = model_inference(model, decoded_image)
    results_df = pd.DataFrame(
        {
            "boxes": [result["boxes"].tolist() for result in results],
            "labels": [result["labels"].tolist() for result in results],
            "scores": [result["scores"].tolist() for result in results],
        }
    ).explode(["boxes", "labels", "scores"], ignore_index=True)

    coords_df = results_df.apply(split_box, axis=1).rename(
        columns={0: "xmin", 1: "ymin", 2: "xmax", 3: "ymax"}
    )
    out_df = pd.concat([results_df, coords_df], axis=1).drop("boxes", axis=1)

    return out_df


def convert_image(image_np):
    image = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB).astype(np.float32)
    image /= 255.0
    image = np.transpose(image, (2, 0, 1)).astype(float)
    tensor_image = torch.tensor(image, dtype=torch.float)
    tensor_image = torch.unsqueeze(tensor_image, 0)
    return tensor_image


def model_inference(model, image_np):
    model.eval()
    tensor_image = convert_image(image_np)
    with torch.no_grad():
        result = model(tensor_image)
    result = [{k: v.to("cpu") for k, v in t.items()} for t in result]
    return result


if __name__ == "__main__":
    model_state_dict = load_model("model_state_dict.htp")
    image = "display_imgs/scratches_261.jpg"

    result = score_unstructured(
        model=model_state_dict, data=image, query={"ret_mode": "csv"}
    )
    print(result)
