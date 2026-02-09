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

import argparse
import os
from types import TracebackType
from typing import cast

import datarobot as dr
from alembic import command
from alembic.config import Config
from core.persistent_fs.dr_file_system import all_env_variables_present
from core.persistent_fs.kv_custom_app_implementattion import (
    KeyValue,
    KeyValueEntityType,
)

MIGRATION_LOCK_NAME = "alembic_migration_lock"


class MigrationLock:
    def __init__(
        self, ignore_lock: bool = False, client: dr.rest.RESTClientObject | None = None
    ):
        self.environment_is_set = all_env_variables_present()
        self.client = client
        self.lock: KeyValue | None = None
        self.ignore_lock = ignore_lock

        if self.environment_is_set and not self.client:
            self.client = dr.Client(
                token=os.environ["DATAROBOT_API_TOKEN"],
                endpoint=os.environ["DATAROBOT_ENDPOINT"],
            )

    def __enter__(self) -> None:
        if self._get_lock_value() and not self.ignore_lock:
            # migration is already in process
            raise RuntimeError(
                f"Migration for app #{os.environ['APPLICATION_ID']} is already in process"
            )
        self._set_lock_value(True)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._set_lock_value(False)

    def _get_lock_value(self) -> bool:
        if not self.environment_is_set:
            return False
        with self.client:  # type: ignore[union-attr]
            if self.lock:
                self.lock.refresh()
            else:
                self.lock = KeyValue.find(
                    os.environ["APPLICATION_ID"],
                    KeyValueEntityType.CUSTOM_APPLICATION,
                    MIGRATION_LOCK_NAME,
                )

        if not self.lock:
            return False
        return cast(bool, self.lock.get_value())

    def _set_lock_value(self, value: bool) -> None:
        if not self.environment_is_set:
            return
        with self.client:  # type: ignore[union-attr]
            if self.lock:
                self.lock.update(value=value)
            else:
                self.lock = KeyValue.create(
                    entity_id=os.environ["APPLICATION_ID"],
                    entity_type=KeyValueEntityType.CUSTOM_APPLICATION,
                    name=MIGRATION_LOCK_NAME,
                    category=dr.KeyValueCategory.ARTIFACT,
                    value_type=dr.KeyValueType.BOOLEAN,
                    value=value,
                )


def run_alembic_upgrade(ignore_lock: bool = False) -> None:
    # Construct the path to alembic.ini relative to the script's location
    current_dir = os.path.dirname(os.path.abspath(__file__))
    alembic_ini_path = os.path.join(current_dir, "alembic.ini")

    # Load Alembic configuration
    alembic_cfg = Config(alembic_ini_path)

    # Set the script location if it's not in the same directory as alembic.ini
    # This is often needed if your migrations are in a 'migrations' subfolder
    # alembic_cfg.set_main_option("script_location", os.path.join(current_dir, "migrations"))

    # Run the upgrade command to the latest revision
    with MigrationLock(ignore_lock):
        print("Running Alembic upgrade to 'head'...")
        command.upgrade(alembic_cfg, "head")
        print("Alembic upgrade completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="AlembicMigration",
        description="Performs migration and makes sure that only one at the time is running.",
    )
    parser.add_argument(
        "-i",
        "--ignore-lock",
        action="store_true",
        help="Ignore lock when running migration",
    )
    args = parser.parse_args()

    run_alembic_upgrade(args.ignore_lock)
