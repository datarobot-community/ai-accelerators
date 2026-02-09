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
import asyncio
import os
import sqlite3
from typing import Any, Callable, Self, cast

import aiosqlite

from core.persistent_fs.dr_file_system import DRFileSystem, calculate_checksum


def _get_fs_entity() -> DRFileSystem | None:
    return DRFileSystem() if os.environ.get("APPLICATION_ID") else None


class AIOSqliteConnectionExtension(aiosqlite.Connection):
    def __init__(
        self,
        connector: Callable[[], sqlite3.Connection],
        iter_chunk_size: int,
        loop: asyncio.AbstractEventLoop | None = None,
        database_path: str | None = None,
    ):
        super().__init__(connector, iter_chunk_size, loop)
        self._database_path = database_path
        self._checksum = b""
        self._fs_entity = _get_fs_entity()

    def _preload_file(self) -> None:
        if not self._fs_entity:
            return
        if not self._database_path or self._database_path == ":memory:":
            return
        if not self._fs_entity.exists(self._database_path):
            return

        self._fs_entity.get(
            self._database_path, self._database_path
        )  # get file with the same name from persistent storage

        self._checksum = calculate_checksum(self._database_path)

    async def _connect(self) -> Self:
        self._preload_file()
        return await super()._connect()  # type: ignore[return-value]

    async def close(self) -> None:
        await super().close()
        if not self._fs_entity:
            return
        if not self._database_path or self._database_path == ":memory:":
            return
        new_checksum = calculate_checksum(self._database_path)
        if new_checksum == self._checksum:
            return
        self._fs_entity.put(self._database_path, self._database_path)
        self._checksum = new_checksum


def connect_dr_fs(  # type: ignore[no-untyped-def]
    database: str | bytes,
    *,
    iter_chunk_size=64,
    loop: asyncio.AbstractEventLoop | None = None,
    **kwargs: Any,
) -> AIOSqliteConnectionExtension:
    """Create and return a connection proxy to the sqlite database."""

    if isinstance(database, str):
        loc = database
    elif isinstance(database, bytes):
        loc = database.decode("utf-8")
    else:
        loc = str(database)

    def connector() -> sqlite3.Connection:
        return cast(sqlite3.Connection, sqlite3.connect(loc, **kwargs))

    return AIOSqliteConnectionExtension(
        connector, iter_chunk_size, loop, database_path=loc
    )
