# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import io
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from typing import (
    Any,
    BinaryIO,
    Callable,
    ParamSpec,
    TypeVar,
    cast,
)

import datarobot as dr
from fsspec import AbstractFileSystem

from core.persistent_fs.kv_custom_app_implementattion import (
    KeyValue,
    KeyValueEntityType,
)

Path = str
NodeInfo = dict[str, str | int | float]
Metadata = dict[Path, NodeInfo]

CatalogId = str
LocalFileInfo = tuple[str, float]
LocalFilesMetadata = dict[CatalogId, LocalFileInfo]

WrapperParams = ParamSpec("WrapperParams")
WrapperReturnType = TypeVar("WrapperReturnType")

logger = logging.getLogger(__name__)

METADATA_STORAGE_NAME = "fs_metadata"
TIMESTAMP_STORAGE_NAME = "fs_timestamp"

FILE_API_CONNECT_TIMEOUT = float(os.environ.get("FILE_API_CONNECT_TIMEOUT", 180))
FILE_API_READ_TIMEOUT = float(os.environ.get("FILE_API_READ_TIMEOUT", 180))


def _keep_metadata_in_sync(
    func: Callable[WrapperParams, WrapperReturnType],
) -> Callable[WrapperParams, WrapperReturnType]:
    def wrapper(
        *args: WrapperParams.args, **kwargs: WrapperParams.kwargs
    ) -> WrapperReturnType:
        fs_entity: "DRFileSystem" = cast("DRFileSystem", args[0])
        logger.debug(
            "Entering metadata sync wrapper.", extra={"stack": fs_entity._sync_stack}
        )
        fs_entity._sync_stack.append(func.__name__)
        if (
            len(fs_entity._sync_stack) == 1
            and not fs_entity._remote_metadata_was_updated()
        ):
            fs_entity._refresh_local_metadata()

        try:
            result = func(*args, **kwargs)
        except Exception:
            logger.debug(
                "Exception caught by sync wrapper.",
                extra={"function": func.__name__, "stack": fs_entity._sync_stack},
            )
            fs_entity._sync_stack.pop()
            raise

        if len(fs_entity._sync_stack) == 1 and fs_entity._local_metadata_was_updated():
            fs_entity._update_stored_metadata()
        fs_entity._sync_stack.pop()
        logger.debug(
            "Exiting metadata sync wrapper.", extra={"stack": fs_entity._sync_stack}
        )
        return result

    return wrapper


class DRFileSystem(AbstractFileSystem):  # type: ignore[misc]
    """
    DRFileSystem is fsspec implementation for interact with Datarobot
    KeyValue and File storage for having persistent storage inside
    custom applications.
    """

    protocol = "dr"

    def __init__(
        self,
        dr_client: dr.rest.RESTClientObject | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.client = dr_client or dr.Client(
            token=os.environ.get("DATAROBOT_API_TOKEN"),
            endpoint=os.environ.get("DATAROBOT_ENDPOINT"),
        )
        self.app_id: str = os.environ.get("APPLICATION_ID")  # type: ignore[assignment]
        if not self.app_id:
            raise ValueError("APPLICATION_ID env variable is not set.")

        self._temp_dir = tempfile.mkdtemp()
        self._downloaded_files: LocalFilesMetadata = {}

        self._fs_metadata: Metadata = {}
        self._fs_metadata_timestamp: float = 0.0  # timestamp of when we have data

        self._fs_metadata_stored: KeyValue | None = None  # remotely stored metadata
        self._fs_metadata_timestamp_stored: KeyValue | None = (
            None  # remotely stored timestamp
        )

        self._sync_stack: list[
            str
        ] = []  # making sure that local metadata fetched for first and updated for last nested call

        logger.debug("Initialized DRFileSystem.", extra={"tmp_dir": self._temp_dir})

    def __del__(self) -> None:
        """Cleanup temporary directory on object destruction."""
        if os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir)

    def _refresh_fs_metadata_timestamp_stored(self) -> None:
        with self.client:
            if self._fs_metadata_timestamp_stored:
                self._fs_metadata_timestamp_stored.refresh()
            else:
                self._fs_metadata_timestamp_stored = KeyValue.find(
                    self.app_id,
                    KeyValueEntityType.CUSTOM_APPLICATION,
                    TIMESTAMP_STORAGE_NAME,
                )

    def _refresh_fs_metadata_stored(self) -> None:
        with self.client:
            if self._fs_metadata_stored:
                self._fs_metadata_stored.refresh()
            else:
                self._fs_metadata_stored = KeyValue.find(
                    self.app_id,
                    KeyValueEntityType.CUSTOM_APPLICATION,
                    METADATA_STORAGE_NAME,
                )

    def _remote_metadata_was_updated(self) -> bool:
        self._refresh_fs_metadata_timestamp_stored()
        if not self._fs_metadata_timestamp_stored:
            return True
        return (
            self._fs_metadata_timestamp_stored.numeric_value
            <= self._fs_metadata_timestamp
        )

    def _local_metadata_was_updated(self) -> bool:
        if self._fs_metadata_timestamp == 0:
            return False
        if not self._fs_metadata_timestamp_stored:
            return True
        return (
            self._fs_metadata_timestamp
            > self._fs_metadata_timestamp_stored.numeric_value
        )

    def _update_stored_metadata(self) -> None:
        logger.debug("Updating metadata in persistent storage.")
        with self.client:
            if self._fs_metadata_timestamp_stored:
                self._fs_metadata_timestamp_stored.update(
                    value=self._fs_metadata_timestamp
                )
            else:
                self._fs_metadata_timestamp_stored = KeyValue.create(
                    entity_id=self.app_id,
                    entity_type=KeyValueEntityType.CUSTOM_APPLICATION,
                    name=TIMESTAMP_STORAGE_NAME,
                    category=dr.KeyValueCategory.ARTIFACT,
                    value_type=dr.KeyValueType.NUMERIC,
                    value=self._fs_metadata_timestamp,
                )

            if self._fs_metadata_stored:
                self._fs_metadata_stored.update(value=json.dumps(self._fs_metadata))
            else:
                self._fs_metadata_stored = KeyValue.create(
                    entity_id=self.app_id,
                    entity_type=KeyValueEntityType.CUSTOM_APPLICATION,
                    name=METADATA_STORAGE_NAME,
                    category=dr.KeyValueCategory.ARTIFACT,
                    value_type=dr.KeyValueType.JSON,
                    value=json.dumps(self._fs_metadata),
                )

    def _refresh_local_metadata(self) -> None:
        logger.debug("Updating local metadata from persistent storage.")
        self._refresh_fs_metadata_timestamp_stored()
        if self._fs_metadata_timestamp_stored:
            self._fs_metadata_timestamp = (
                self._fs_metadata_timestamp_stored.numeric_value
            )

        self._refresh_fs_metadata_stored()
        if self._fs_metadata_stored:
            self._fs_metadata = json.loads(self._fs_metadata_stored.value)

    @_keep_metadata_in_sync
    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        logger.debug(
            "Making directory.", extra={"path": path, "create_parents": create_parents}
        )
        path = self._strip_protocol(path)
        if self.exists(path):
            if create_parents:
                return
            else:
                raise FileExistsError()

        parent = self._parent(path)
        if parent and not self.exists(parent):
            if create_parents:
                self.makedir(parent, create_parents=True, **kwargs)
            else:
                raise FileNotFoundError()
        clean_path = path.rstrip("/")
        self._fs_metadata[clean_path] = {
            "type": "directory",
            "name": clean_path,
            "modified_at": time.time(),
        }
        self._fs_metadata_timestamp = time.time()

    @_keep_metadata_in_sync
    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        logger.debug("Making directories.", extra={"path": path, "exist_ok": exist_ok})
        path = self._strip_protocol(path)
        if self.exists(path) and not exist_ok:
            raise FileExistsError()

        self.mkdir(path, create_parents=True)

    @_keep_metadata_in_sync
    def rmdir(self, path: str) -> None:
        logger.debug("Removing directory.", extra={"path": path})
        path = self._strip_protocol(path)
        if not self.exists(path):
            raise FileNotFoundError()
        if not self.isdir(path):
            raise ValueError(f"{path} is not a directory")
        if self.ls(path, detail=False):
            raise ValueError(f"{path} is not empty")

        self._fs_metadata.pop(path, None)
        self._fs_metadata_timestamp = time.time()

    @_keep_metadata_in_sync
    def ls(
        self, path: str, detail: bool = True, **kwargs: Any
    ) -> list[str] | list[dict[str, Any]]:
        logger.debug(
            "Providing directory info.", extra={"path": path, "detail": detail}
        )
        path = self._strip_protocol(path)
        clean_path = path.rstrip("/")
        # empty clean_path is root
        if clean_path and clean_path not in self._fs_metadata:
            raise FileNotFoundError()
        if clean_path and self._fs_metadata[clean_path].get("type") != "directory":
            return []
        children = {
            p
            for p in self._fs_metadata.keys()
            if p.startswith(clean_path) and "/" not in p[len(clean_path) + 1 :]
        }
        children.discard(clean_path)
        ordered_children = sorted(children)
        if detail:
            return [self._fs_metadata[c] for c in ordered_children]
        return ordered_children

    @_keep_metadata_in_sync
    def modified(self, path: str) -> float:
        if not self.exists(path):
            raise FileNotFoundError()
        return cast(float, self.info(path).get("modified_at", 0.0))

    @_keep_metadata_in_sync
    def _open(self, path: str, mode: str = "rb", **kwargs: Any) -> BinaryIO:
        logger.debug("Opening file.", extra={"path": path, "mode": mode})
        path = self._strip_protocol(path)

        if mode not in ["rb", "wb"]:
            raise NotImplementedError("Only read and write modes are supported")

        if mode == "rb":
            if not self.exists(path):
                raise FileNotFoundError()
            if not self.isfile(path):
                raise ValueError(f"{path} is not a file")
            local_path = self._get_local_path(self.info(path))
            return cast(BinaryIO, open(local_path, mode))
        elif mode == "wb":
            parent = self._parent(path)
            if not self.exists(parent):
                raise FileNotFoundError(parent)
            if not self.isdir(parent):
                raise ValueError(f"{parent} is not a directory")
            local_path = os.path.join(self._temp_dir, str(uuid.uuid4()))
            return _FileIOWrapper(
                fs_entity=self, virtual_path=path, name=local_path, mode=mode
            )
        else:
            raise NotImplementedError()

    def _get_local_path(self, file_info: dict[str, Any]) -> str:
        catalog_id = file_info.get("catalog_id")
        if not catalog_id:
            raise ValueError(f"{file_info} is missing catalog_id")
        if file_info["catalog_id"] not in self._downloaded_files:
            # there is no local copy
            return self._download_file(file_info)
        local_path, local_copy_update_time = self._downloaded_files[
            file_info["catalog_id"]
        ]
        if file_info["modified_at"] > local_copy_update_time:
            # local copy is outdated
            return self._download_file(file_info)
        return local_path

    def _download_file(self, file_info: dict[str, Any]) -> str:
        catalog_id = file_info.get("catalog_id")
        if not catalog_id:
            raise ValueError(f"{file_info} is missing catalog_id")

        local_path = os.path.join(self._temp_dir, catalog_id)
        logger.debug(
            "Downloading file from catalog.",
            extra={"catalog_id": catalog_id, "local_path": local_path},
        )

        response = self.client.get(
            f"files/{catalog_id}/file/",
            timeout=(FILE_API_CONNECT_TIMEOUT, FILE_API_READ_TIMEOUT),
        )
        with open(local_path, "wb") as f:
            f.write(response.content)

        self._downloaded_files[catalog_id] = (
            local_path,
            file_info.get("modified_at", 0),
        )
        return local_path

    def _remove_catalog_item(self, catalog_id: str) -> None:
        logger.debug("Removing file from catalog.", extra={"catalog_id": catalog_id})
        self.client.delete(f"files/{catalog_id}/")

    @_keep_metadata_in_sync
    def _upload_to_catalog(self, virtual_path: str, local_path: str) -> None:
        logger.debug("Uploading file to catalog.", extra={"virtual_path": virtual_path})
        with open(local_path, "rb") as f:
            response = self.client.post(
                "files/fromFile/",
                files={"file": (virtual_path, f)},
                data={"useArchiveContents": "false"},
                timeout=(FILE_API_CONNECT_TIMEOUT, FILE_API_READ_TIMEOUT),
            )
        catalog_id = response.json()["catalogId"]
        modified_at = time.time()
        fs_info = {
            "catalog_id": catalog_id,
            "type": "file",
            "name": virtual_path,
            "modified_at": modified_at,
            "size": os.path.getsize(local_path),
        }
        self._downloaded_files[catalog_id] = (local_path, modified_at)
        existing_info = self._fs_metadata.get(virtual_path)
        if existing_info:
            catalog_id = cast(str, existing_info["catalog_id"])
            self._remove_catalog_item(catalog_id)
            local_path, _ = self._downloaded_files.pop(catalog_id, ("", 0.0))
            if local_path:
                os.remove(local_path)
        self._fs_metadata[virtual_path] = fs_info
        self._fs_metadata_timestamp = modified_at

    @_keep_metadata_in_sync
    def rm_file(self, path: str) -> None:
        logger.debug("Removing node.", extra={"path": path})
        if not self.exists(path):
            raise FileNotFoundError()
        if self.isdir(path):
            self.rmdir(path)
            return
        if self.isfile(path):
            clear_path = self._strip_protocol(path).rstrip("/")
            info = self._fs_metadata[clear_path]
            catalog_id = cast(str, info["catalog_id"])
            self._remove_catalog_item(catalog_id)
            local_path, _ = self._downloaded_files.pop(catalog_id, ("", 0.0))
            if local_path:
                os.remove(local_path)

            self._fs_metadata.pop(clear_path)
            self._fs_metadata_timestamp = time.time()
            return
        raise NotImplementedError(f"No remove logic for node: {path}")

    @_keep_metadata_in_sync
    def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:
        logger.debug("Copy file.", extra={"src_path": path1, "dst_path": path2})
        if not self.exists(path1):
            raise FileNotFoundError()
        if self.exists(path2):
            raise FileExistsError()
        if self.isdir(path1):
            self.mkdir(path2)
            return
        if self.isfile(path1):
            parent = self._parent(path2)
            if not self.exists(parent):
                raise FileNotFoundError(parent)
            if not self.isdir(parent):
                raise ValueError(f"{parent} is not a directory")

            local_path = self._get_local_path(self.info(path1))
            self._upload_to_catalog(self._strip_protocol(path2).rstrip("/"), local_path)
            return
        raise NotImplementedError(f"No copy logic for node: {path1}")


def calculate_checksum(path: str) -> bytes:
    adder = hashlib.sha256()
    with open(path, "rb") as file:
        while chunk := file.read(8192):
            adder.update(chunk)
    return adder.digest()


def all_env_variables_present() -> bool:
    # check if all env variables are present
    expected_envs = ["DATAROBOT_ENDPOINT", "DATAROBOT_API_TOKEN", "APPLICATION_ID"]
    return not any(not os.environ.get(env_name) for env_name in expected_envs)


class _FileIOWrapper(io.FileIO):
    def __init__(
        self, fs_entity: DRFileSystem, virtual_path: str, name: str, mode: str
    ) -> None:
        super().__init__(name, mode)
        self._fs_entity = fs_entity
        self._virtual_path = virtual_path

    def close(self) -> None:
        upload_file = False
        if not self.closed:
            self.seek(0, io.SEEK_END)
            size = self.tell()
            upload_file = size > 0
        super().close()
        if upload_file:
            self._fs_entity._upload_to_catalog(self._virtual_path, self.name)
        else:
            logger.debug("Wrapper was empty")
