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
import threading
import time

from core.utils.rw_lock import AbstractReadWriteLock, MockReadWriteLock, ThreadReadWriteLock


def thread_read_process(
    lock: AbstractReadWriteLock, data_list: list[str], sleep_time: int, text: str
) -> None:
    with lock.read_lock():
        time.sleep(sleep_time)
        data_list.append(text)


def thread_write_process(
    lock: AbstractReadWriteLock, data_list: list[str], sleep_time: int, text: str
) -> None:
    with lock.write_lock():
        time.sleep(sleep_time)
        data_list.append(text)


def test_thread_read_write_lock() -> None:
    result: list[str] = []
    lock = ThreadReadWriteLock()
    treads = [
        threading.Thread(target=thread_read_process, args=(lock, result, 4, "read_2")),
        threading.Thread(target=thread_read_process, args=(lock, result, 3, "read_1")),
        threading.Thread(
            target=thread_write_process, args=(lock, result, 3, "write_1")
        ),
        threading.Thread(target=thread_read_process, args=(lock, result, 1, "read_3")),
        threading.Thread(
            target=thread_write_process, args=(lock, result, 1, "write_2")
        ),
    ]

    # two read thread with 4s and 3s sleep time, should be executed in parallel and make write operation wait
    treads[0].start()
    treads[1].start()
    # write operation after read operation already started, should prevent all other operations
    time.sleep(1)
    treads[2].start()
    time.sleep(1)
    # read and write operations added while previous write operation in process
    # if write and read operation waiting, write operation should be executed next
    treads[3].start()
    treads[4].start()

    for t in treads:
        t.join()

    expected_result = [
        "read_1",
        "read_2",
        "write_1",
        "write_2",
        "read_3",
    ]

    assert expected_result == result


def test_mock_read_write_lock() -> None:
    # same RW lock interface, but no locks
    result: list[str] = []
    lock = MockReadWriteLock()
    treads = [
        threading.Thread(target=thread_read_process, args=(lock, result, 1, "read_1")),
        threading.Thread(
            target=thread_write_process, args=(lock, result, 2, "write_1")
        ),
        threading.Thread(target=thread_read_process, args=(lock, result, 1, "read_2")),
    ]

    treads[0].start()
    time.sleep(1)
    treads[1].start()
    treads[2].start()

    for t in treads:
        t.join()

    # no locks so execution order should be the same as pause
    expected_result = [
        "read_1",
        "read_2",
        "write_1",
    ]

    assert expected_result == result
