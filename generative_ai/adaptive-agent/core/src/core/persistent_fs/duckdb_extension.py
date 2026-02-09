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
import os
from types import TracebackType
from typing import Any, Self

import duckdb

from core.persistent_fs.dr_file_system import DRFileSystem, calculate_checksum


def _get_fs_entity() -> DRFileSystem | None:
    return DRFileSystem() if os.environ.get("APPLICATION_ID") else None


class DuckDBPyConnectionWrapper:
    def __init__(
        self,
        connection_entity: duckdb.DuckDBPyConnection,
        database: Any,
        read_only: bool,
        checksum: bytes,
    ):
        self._connection_entity = connection_entity
        self._database = database
        self._read_only = read_only
        self._checksum = checksum
        self._fs_entity = _get_fs_entity()
        if self._fs_entity and not self._connection_entity.filesystem_is_registered(
            self._fs_entity.protocol
        ):
            self._connection_entity.register_filesystem(self._fs_entity)

    def close(self) -> None:
        self._connection_entity.close()
        if self._read_only:
            # skip upload if no write actions
            return
        if not self._database or self._database == ":memory:":
            # skip upload if it was in memory DB
            return
        if not self._fs_entity:
            # skip upload if there is no access to persistent storage FS
            return
        new_checksum = calculate_checksum(self._database)
        if new_checksum == self._checksum:
            # skip upload if nothing has changed
            return
        self._fs_entity.put(self._database, self._database)
        self._checksum = new_checksum

    def duplicate(self) -> Self:
        return self.__class__(
            self._connection_entity.duplicate(),
            self._database,
            self._read_only,
            self._checksum,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection_entity, name)

    def __enter__(self) -> duckdb.DuckDBPyConnection:
        return self._connection_entity.__enter__()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._connection_entity.__exit__(exc_type, exc_val, exc_tb)
        self.close()


def _preload_file(database: str | None) -> bytes:
    checksum = b""
    if not database or database == ":memory:":
        return checksum
    fs_entity = _get_fs_entity()
    if not fs_entity:
        return checksum
    if not fs_entity.exists(database):
        return checksum

    fs_entity.get(
        database, database
    )  # get file with the same name from persistent storage

    return calculate_checksum(database)


def connect_dr_fs(
    database: str | None = None,
    read_only: bool = False,
    config: dict[str, Any] | None = None,
) -> DuckDBPyConnectionWrapper:
    # None is acceptable in __doc__ but raise error in reality
    database = database or ":memory:"
    config = config or {}

    checksum = _preload_file(database)

    con = duckdb.connect(database=database, read_only=read_only, config=config)
    return DuckDBPyConnectionWrapper(con, database, read_only, checksum)
