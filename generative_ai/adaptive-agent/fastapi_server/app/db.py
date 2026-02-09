# Copyright 2025 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from asyncio import Lock
from contextlib import asynccontextmanager, nullcontext
from typing import AsyncGenerator, cast

from core.persistent_fs.dr_file_system import (
    DRFileSystem,
    all_env_variables_present,
    calculate_checksum,
)
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import UOWTransaction
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger()


def _prepare_persistence_storage(
    engine: AsyncEngine,
) -> tuple[DRFileSystem, str] | tuple[None, None]:
    if not all_env_variables_present():
        return None, None

    if "sqlite" not in engine.url.drivername:
        return None, None
    if not engine.url.database or ":memory:" == engine.url.database:
        return None, None

    file_path = engine.url.database
    persistent_fs = DRFileSystem()
    return persistent_fs, file_path


class DBCtx:
    def __init__(self, engine: AsyncEngine):
        self.engine = engine

        self._session = async_sessionmaker(
            autoflush=False,
            class_=AsyncSession,
            bind=engine,
            expire_on_commit=False,
        )

        self._persistence_fs: DRFileSystem | None
        self._db_path: str | None
        self._persistence_fs, self._db_path = _prepare_persistence_storage(engine)

        self._lock: Lock | nullcontext = nullcontext()  # type: ignore[type-arg]
        if self._persistence_fs:
            self._lock = Lock()

    @asynccontextmanager
    async def _read_session(self) -> AsyncGenerator[AsyncSession, None]:
        def prevent_writes(
            session_: AsyncSession, flush_context: UOWTransaction, instances: None
        ) -> None:
            if session_.dirty or session_.new or session_.deleted:
                raise RuntimeError(
                    "This session is read-only and cannot perform writes."
                )

        if self._persistence_fs and self._persistence_fs.exists(self._db_path):
            self._persistence_fs.get(self._db_path, self._db_path)

        async with self._session() as session:
            event.listen(session.sync_session, "before_flush", prevent_writes)
            yield session

    @asynccontextmanager
    async def _write_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._lock:
            checksum: bytes | None = None
            if self._persistence_fs and self._persistence_fs.exists(self._db_path):
                self._persistence_fs.get(self._db_path, self._db_path)
                checksum = calculate_checksum(cast(str, self._db_path))

            async with self._session() as session:
                yield session

            if self._persistence_fs:
                new_checksum = calculate_checksum(cast(str, self._db_path))
                if new_checksum != checksum:
                    self._persistence_fs.put(self._db_path, self._db_path)

    @asynccontextmanager
    async def session(
        self, writable: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        session_context = self._write_session if writable else self._read_session
        async with session_context() as session:
            yield session

    async def shutdown(self) -> None:
        """
        Dispose of the engine and close all pooled connections.
        Call this on application shutdown.
        """
        await self.engine.dispose()


async def create_db_ctx(db_url: str, log_sql_stmts: bool = False) -> DBCtx:
    async_engine = create_async_engine(
        db_url,
        echo=log_sql_stmts,
    )

    async with async_engine.begin() as conn:
        # testing DB credentials...
        await conn.execute(text("select '1'"))

    return DBCtx(async_engine)
