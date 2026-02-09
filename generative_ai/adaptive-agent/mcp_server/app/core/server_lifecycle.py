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
from typing import Optional

from datarobot_genai.drmcp import BaseServerLifecycle
from fastmcp import FastMCP


class ServerLifecycle(BaseServerLifecycle):
    """
    User-specific server lifecycle implementation.

    This class demonstrates how to extend BaseServerLifecycle for custom user behavior.
    You only need to implement the methods you actually need - all others have safe defaults.
    """

    def __init__(self) -> None:
        """Initialize the ServerLifecycle manager."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._mcp: Optional[FastMCP] = None

    async def pre_server_start(self, mcp: FastMCP) -> None:
        """
        Initialize user-specific resources before server starts.

        Args:
            mcp: The FastMCP instance that will be started
        """
        self._logger.info("Executing pre-server start user actions...")
        self._mcp = mcp

        # Example initialization tasks:
        # - Initialize user-specific resources
        # - Set up connections to external services
        # - Validate user-specific configuration
        # - Prepare any required state

        # Uncomment and implement as needed:
        # await self._initialize_database()
        # await self._connect_to_external_service()
        # self._validate_user_config()

    async def post_server_start(self, mcp: FastMCP) -> None:
        """
        Execute user-specific tasks after server is ready.

        Args:
            mcp: The running FastMCP instance
        """
        self._logger.info("Executing post-server start user actions...")

        # Example post-start tasks:
        # - Register additional runtime handlers
        # - Start background tasks
        # - Initialize delayed resources
        # - Send startup notifications

        # Uncomment and implement as needed:
        # asyncio.create_task(self._background_task())
        # await self._send_startup_notification()

    async def pre_server_shutdown(self, mcp: FastMCP) -> None:
        """
        Clean up user-specific resources before shutdown.

        Args:
            mcp: The running FastMCP instance
        """
        self._logger.info("Executing pre-server shutdown user actions...")

        # Example cleanup tasks:
        # - Close database connections
        # - Save application state
        # - Stop background tasks
        # - Release resources
        # - Send shutdown notifications

        # Uncomment and implement as needed:
        # if self._db_connection:
        #     await self._db_connection.close()
        # await self._save_state()
        # await self._stop_background_tasks()
