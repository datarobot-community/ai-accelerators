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
import pytest

from app.config import Config
from app.db import DBCtx, create_db_ctx
from app.users.user import User, UserCreate, UserRepository
from tests.conftest import migrate_tables_to_db


@pytest.fixture
async def session_user(db_ctx: DBCtx) -> User:
    """Create a test user in the database."""
    user_repo = UserRepository(db_ctx)
    user_data = UserCreate(
        email="test@example.com", first_name="Test", last_name="User"
    )
    user = await user_repo.create_user(user_data)
    return user


@pytest.fixture
async def db_ctx() -> DBCtx:
    """Create an in-memory database context for testing."""
    config = Config(
        database_uri="sqlite+aiosqlite:///:memory:",
        datarobot_endpoint="https://test.datarobot.com",
        datarobot_api_token="test-token",
        session_secret_key="test-key",
        llm_deployment_id="test-deployment",
    )

    db = await create_db_ctx(config.database_uri)
    await migrate_tables_to_db(db)
    return db
