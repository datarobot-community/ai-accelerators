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
from logging.config import fileConfig
from pathlib import Path
from typing import cast

from alembic import context
from core.persistent_fs.dr_file_system import (
    DRFileSystem,
    all_env_variables_present,
    calculate_checksum,
)
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config
from sqlmodel import SQLModel

from app.config import Config as ApplicationConfig

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = convention

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# default class with application config
app_config = ApplicationConfig()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=app_config.database_uri,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def _get_persistence_fs(engine: AsyncEngine) -> DRFileSystem | None:
    if not all_env_variables_present():
        return None
    if "sqlite" not in engine.url.drivername:
        return None
    if not engine.url.database or ":memory:" == engine.url.database:
        return None
    return DRFileSystem()


def _prepare_folder(engine: AsyncEngine) -> None:
    if "sqlite" not in engine.url.drivername:
        return
    if not engine.url.database or ":memory:" == engine.url.database:
        return

    Path(engine.url.database).parent.mkdir(parents=True, exist_ok=True)


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        {"url": app_config.database_uri},
        prefix="",
        poolclass=pool.NullPool,
    )

    # getting DB file from persistent storage if applicable
    fs = _get_persistence_fs(connectable)
    _prepare_folder(connectable)  # create a folder for DB file
    db_path = connectable.url.database
    checksum: bytes | None = None

    if fs and fs.exists(db_path):
        fs.get(db_path, db_path)
        checksum = calculate_checksum(cast(str, db_path))

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

    if fs:
        new_checksum = calculate_checksum(cast(str, db_path))
        if new_checksum != checksum:
            fs.put(db_path, db_path)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
