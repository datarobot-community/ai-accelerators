#!/usr/bin/env python3
# -*- mode: python; python-indent-offset: 4 -*-

import os

import requests

DATASETS = {
    "LC_train.csv": "https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/LC_train.csv",
    "LC_profile.csv": "https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/LC_profile.csv",
    "LC_transactions.csv": "https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/LC_transactions.csv",
}

ENV_AND_JARS = {
    "spark-udf-assembly-0.1.0.jar": "https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/spark-udf-assembly-0.1.0.jar",
    "venv.tar.gz": "https://s3.amazonaws.com/datarobot_public_datasets/ai_accelerators/feature_discovery/venv.tar.gz",
}


def download_files_from_public_s3(files_dict, to_folder):
    for file_name in files_dict:
        url = files_dict[file_name]
        output_name = os.path.join(to_folder, file_name)
        if os.path.exists(output_name):
            print(f"{output_name} already exists")
        else:
            # Download the file
            response = requests.get(url)
            # Save the file with the original name
            with open(output_name, "wb") as file:
                file.write(response.content)
            print(f"Downloaded {file_name} and saved to {output_name}")
