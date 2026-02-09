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

from unittest.mock import MagicMock

import pytest
from mcp.server.fastmcp import FastMCP

from app.core.server_lifecycle import ServerLifecycle


@pytest.fixture
def mock_mcp() -> MagicMock:
    """Create a mock FastMCP instance."""
    mock = MagicMock(spec=FastMCP)
    return mock


@pytest.fixture
def lifecycle() -> ServerLifecycle:
    """Create a ServerLifecycle instance."""
    return ServerLifecycle()


@pytest.mark.asyncio
async def test_init() -> None:
    """Test ServerLifecycle initialization."""
    lifecycle = ServerLifecycle()
    assert lifecycle._mcp is None
    assert lifecycle._logger is not None


@pytest.mark.asyncio
async def test_pre_server_start(
    lifecycle: ServerLifecycle, mock_mcp: MagicMock
) -> None:
    """Test pre_server_start method."""
    await lifecycle.pre_server_start(mock_mcp)
    assert lifecycle._mcp == mock_mcp


@pytest.mark.asyncio
async def test_post_server_start(
    lifecycle: ServerLifecycle, mock_mcp: MagicMock
) -> None:
    """Test post_server_start method."""
    await lifecycle.post_server_start(mock_mcp)
    # Currently just verifies the method runs without errors
    # Add more assertions when post_server_start has actual implementation


@pytest.mark.asyncio
async def test_lifecycle_sequence(
    lifecycle: ServerLifecycle, mock_mcp: MagicMock
) -> None:
    """Test the complete lifecycle sequence."""
    # Test pre-server start
    await lifecycle.pre_server_start(mock_mcp)
    assert lifecycle._mcp == mock_mcp

    # Test post-server start
    await lifecycle.post_server_start(mock_mcp)
    # Add more assertions when actual implementation is added
