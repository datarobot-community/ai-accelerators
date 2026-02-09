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
import asyncio
import threading
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator


class AbstractReadWriteLock:
    @contextmanager
    def read_lock(self) -> Iterator[None]:
        raise NotImplementedError()
        yield  # fixing typecheck

    @contextmanager
    def write_lock(self) -> Iterator[None]:
        raise NotImplementedError()
        yield  # fixing typecheck

    @asynccontextmanager
    async def async_read_lock(self) -> AsyncIterator[None]:
        raise NotImplementedError()
        yield  # fixing typecheck

    @asynccontextmanager
    async def async_write_lock(self) -> AsyncIterator[None]:
        raise NotImplementedError()
        yield  # fixing typecheck


class ThreadReadWriteLock(AbstractReadWriteLock):
    """
    Thread RW Lock. Should allow to have multiple read operations, but write operation block all others.
    Adding write operation to wait list do not allow to execute new read operations.
    We need thread protection because of fastapi.BackgroundTasks
    """

    def __init__(self) -> None:
        lock = threading.Lock()
        self._reader_cond = threading.Condition(lock)
        self._writer_cond = threading.Condition(lock)
        self._readers = 0
        self._writers_waiting = 0
        self._writer = False

    def _acquire_read(self) -> None:
        with self._reader_cond:
            while self._writer or self._writers_waiting > 0:
                self._reader_cond.wait()
            self._readers += 1

    def _release_read(self) -> None:
        with self._reader_cond:
            self._readers -= 1
            if self._readers == 0:
                self._writer_cond.notify(1)

    def _acquire_write(self) -> None:
        with self._writer_cond:
            self._writers_waiting += 1
            while self._writer or self._readers > 0:
                self._writer_cond.wait()
            self._writers_waiting -= 1
            self._writer = True

    def _release_write(self) -> None:
        with self._writer_cond:
            self._writer = False
            if self._writers_waiting > 0:
                self._writer_cond.notify(1)
            else:
                self._reader_cond.notify_all()

    @contextmanager
    def read_lock(self) -> Iterator[None]:
        self._acquire_read()
        try:
            yield
        finally:
            self._release_read()

    @contextmanager
    def write_lock(self) -> Iterator[None]:
        self._acquire_write()
        try:
            yield
        finally:
            self._release_write()

    @asynccontextmanager
    async def async_read_lock(self) -> AsyncIterator[None]:
        await asyncio.to_thread(self._acquire_read)
        try:
            yield
        finally:
            await asyncio.to_thread(self._release_read)

    @asynccontextmanager
    async def async_write_lock(self) -> AsyncIterator[None]:
        await asyncio.to_thread(self._acquire_write)
        try:
            yield
        finally:
            await asyncio.to_thread(self._release_write)


class MockReadWriteLock(AbstractReadWriteLock):
    """
    Has the same interface as ThreadReadWriteLock but do no blocking.
    Should be used for cases when lock is no need, like interaction with external DB.
    """

    @contextmanager
    def read_lock(self) -> Iterator[None]:
        yield

    @contextmanager
    def write_lock(self) -> Iterator[None]:
        yield

    @asynccontextmanager
    async def async_read_lock(self) -> AsyncIterator[None]:
        yield

    @asynccontextmanager
    async def async_write_lock(self) -> AsyncIterator[None]:
        yield
