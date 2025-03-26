import logging
from typing import Any, Dict

import pandas as pd
import requests

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def get_prompt_count(playground_id: str, headers: Dict[str, str], endpoint: str) -> int:
    url = (
        f"{endpoint}/genai/playgrounds/{playground_id}/trace/?limit=1&sortBy=timestamp"
    )

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("totalCount")
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")


def flatten_json(data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    flattened = {}
    for key, value in data.items():
        if isinstance(value, dict) and key != "metrics":
            flattened.update(flatten_json(value, f"{prefix}{key}_"))
        elif isinstance(value, list) and key == "metrics":
            # Special handling for metrics
            for metric in value:
                if metric.get("name") and metric.get("value") is not None:
                    metric_name = f"metrics_{metric['name']}"
                    flattened[metric_name] = metric["value"]
        elif not isinstance(value, (dict, list)):
            flattened[f"{prefix}{key}"] = value
    return flattened


def get_trace_data(
    playground_id: str, headers: Dict[str, str], endpoint: str
) -> pd.DataFrame:
    def _fetch_page(url: str) -> tuple[list, str]:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")

        json_data = response.json()
        return json_data.get("data", []), json_data.get("next")

    all_data = []
    url = (
        f"{endpoint}/genai/playgrounds/{playground_id}/trace/?limit=50&sortBy=timestamp"
    )

    # Fetch all pages recursively
    while url:
        data_list, next_url = _fetch_page(url)
        all_data.extend(data_list)
        url = next_url  # If next_url is None, the loop will end

    # Flatten each item in the data array
    flattened_data = [flatten_json(item) for item in all_data]

    # Convert to DataFrame
    df = pd.DataFrame(flattened_data)

    return df
