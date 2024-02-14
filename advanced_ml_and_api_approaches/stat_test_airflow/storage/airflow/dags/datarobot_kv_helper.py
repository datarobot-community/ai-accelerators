import json
import os

import requests


class KVCategory:
    TRAINING_PARAMETER = "trainingParameter"
    METRIC = "metric"
    TAG = "tag"
    ARTIFACT = "artifact"
    RUNTIME_PARAMETER = "runtimeParameter"


class KVValueType:
    STRING = "string"
    IMAGE = "image"
    DATASET = "dataset"

    @staticmethod
    def path_to_artifact_type(path: str):
        if path.endswith((".png", ".jpg", "jpeg", ".JPEG", ".JPG")):
            return KVValueType.IMAGE
        if path.endswith((".csv", ".CSV")):
            return KVValueType.DATASET
        return None


class KVEntityType:
    MODEL_PACKAGE = "modelPackage"


class KVInfo:
    def __init(self):
        self.id = None
        self.name = None
        self.value = None
        self.value_type = None


class DataRobotKeyValueHelper:
    """
    A Helper class to interact with DataRobot Key Value feature.
    """

    AUTHORIZATION_TOKEN_PREFIX = "Bearer "
    KV_API_ENDPOINT = "/api/v2/keyValues/"
    KV_FROM_FILE = "fromFile"

    def __init__(
        self,
        datarobot_uri: str = None,
        datarobot_token: str = None,
        entity_id: str = None,
        entity_type: str = KVEntityType.MODEL_PACKAGE,
        verify_ssl: bool = True,
        allow_update: bool = False,
    ):
        """
        Provide access to DataRobot KeyValue framework
        :param datarobot_uri:
        :param datarobot_token:
        :param entity_id:
        :param entity_type:
        :param verify_ssl:
        :param allow_update_dr_key: If value is True then update the content of the DataRobot key
            value in case it already exists.
        :return:
        """
        # self._header =  'Authorization: Token hunter2' --header 'Content-Type: application/json'
        self._datarobot_uri = datarobot_uri
        self._datarobot_token = datarobot_token
        self._entity_id = entity_id
        self._entity_type = entity_type
        self._api_key = (
            DataRobotKeyValueHelper.AUTHORIZATION_TOKEN_PREFIX + self._datarobot_token
        )
        self._common_headers = {"Authorization": self._api_key}
        self._verify = verify_ssl
        self._allow_update = allow_update

    def get_all_kv(self, entity_id=KVEntityType.MODEL_PACKAGE):
        url = self._datarobot_uri + DataRobotKeyValueHelper.KV_API_ENDPOINT
        headers = dict(self._common_headers)
        response = requests.get(url, headers=headers, verify=self._verify)
        if not response.ok:
            return
        kv_list = response.json()["data"]
        return kv_list

    def get_kv_id(self, name, category):
        kv_list = self.get_all_kv()
        for kvinfo in kv_list:
            if kvinfo["name"] == name and kvinfo["category"] == category:
                return kvinfo["id"]
        return None

    def delete_all_kv(self):
        """
        Delete all KV of an entity - this can be useful if some issue was detected while creating
        kv on a model in the registry and we will to start from fresh
        :return:
        """
        url = self._datarobot_uri + DataRobotKeyValueHelper.KV_API_ENDPOINT
        headers = dict(self._common_headers)

        kv_list = self.get_all_kv()
        for kvinfo in kv_list:
            delete_uri = url + "/" + kvinfo["id"]
            # print(delete_uri)
            response = requests.delete(delete_uri, headers=headers, verify=self._verify)
            # print(response)
            if not response.ok:
                print(response.text)

    def delete_kv(self, name, category):
        headers = dict(self._common_headers)

        kv_id = self.get_kv_id(name, category)
        if kv_id is None:
            return None
        url = (
            self._datarobot_uri + DataRobotKeyValueHelper.KV_API_ENDPOINT + "/" + kv_id
        )
        response = requests.delete(url, headers=headers, verify=self._verify)
        if not response.ok:
            print(response.text)

    def set_kv(
        self,
        name: str,
        category: str,
        description: str = "",
        value=None,
        value_type: str = KVValueType.STRING,
    ):
        url = self._datarobot_uri + DataRobotKeyValueHelper.KV_API_ENDPOINT
        data = {
            "name": name,
            "category": category,
            "description": description,
            "entityId": self._entity_id,
            "entityType": self._entity_type,
            "value": value,
            "valueType": value_type,
        }

        headers = dict(self._common_headers)
        headers.update({"Content-Type": "application/json"})
        response = requests.post(
            url, data=json.dumps(data), headers=headers, verify=self._verify
        )
        if not response.ok:
            print(response.text)
            return False
        return True

    def set_parameter(self, name, value):
        return self.set_kv(
            name,
            category=KVCategory.TRAINING_PARAMETER,
            value=value,
            value_type=KVValueType.STRING,
        )

    def set_metric(self, name, value):
        if isinstance(value, (int, float)):
            value = "{:.5f}".format(value)
        return self.set_kv(
            name, category=KVCategory.METRIC, value=value, value_type=KVValueType.STRING
        )

    def set_tag(self, name: str, value: str):
        return self.set_kv(
            name, category=KVCategory.TAG, value=value, value_type=KVValueType.STRING
        )

    def set_artifact(
        self, name: str, path: str, artifact_type: str, description: str = None
    ):
        if not os.path.exists(path):
            raise Exception("Path {} does not exists".format(path))
        if os.path.isdir(path):
            raise Exception("Directory artifacts are not supported")
        if artifact_type not in (KVValueType.IMAGE, KVValueType.DATASET):
            raise Exception("Supported artifacts are only images and datasets")

        url = (
            self._datarobot_uri
            + DataRobotKeyValueHelper.KV_API_ENDPOINT
            + DataRobotKeyValueHelper.KV_FROM_FILE
        )
        data = {
            "name": name,
            "category": KVCategory.ARTIFACT,
            "entityId": self._entity_id,
            "entityType": self._entity_type,
            "valueType": artifact_type,
        }
        if description:
            data["description"] = description

        headers = dict(self._common_headers)
        files = {"file": open(path, "rb")}
        response = requests.post(
            url, data=data, files=files, headers=headers, verify=self._verify
        )
        if not response.ok:
            print(response.text)
