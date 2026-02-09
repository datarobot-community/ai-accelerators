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
import os
import sys
from typing import Any

from datarobot_genai.drmcp import create_mcp_server

from app.core.server_lifecycle import ServerLifecycle
from app.core.user_config import get_user_config
from app.core.user_credentials import get_user_credentials


def suppress_keyboard_interrupt_traceback(
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_traceback: Any | None,
) -> None:
    """Suppress traceback for KeyboardInterrupt, exit cleanly for other exceptions."""
    if exc_type is KeyboardInterrupt:
        # Suppress KeyboardInterrupt traceback
        sys.exit(0)
    # Use default exception handler for other exceptions
    if exc_type is not None and exc_value is not None:
        sys.__excepthook__(exc_type, exc_value, exc_traceback)


def handle_asyncio_exception(
    loop: asyncio.AbstractEventLoop, context: dict[str, Any]
) -> None:
    """Handle exceptions in asyncio tasks, suppressing KeyboardInterrupt tracebacks."""
    exception = context.get("exception")
    if isinstance(exception, KeyboardInterrupt):
        # Suppress KeyboardInterrupt tracebacks during shutdown
        return
    # Let other exceptions be handled normally
    default_handler = loop.default_exception_handler
    if default_handler is not None:
        default_handler(context)


class CustomEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    """Custom event loop policy that sets exception handler for KeyboardInterrupt."""

    def new_event_loop(self) -> asyncio.AbstractEventLoop:
        loop = super().new_event_loop()
        loop.set_exception_handler(handle_asyncio_exception)
        return loop


if __name__ == "__main__":
    # Suppress KeyboardInterrupt tracebacks globally
    sys.excepthook = suppress_keyboard_interrupt_traceback

    # Set custom event loop policy to handle KeyboardInterrupt in asyncio tasks
    # even when the loop is created inside server.run()
    asyncio.set_event_loop_policy(CustomEventLoopPolicy())

    # Get paths to user modules
    app_dir = os.path.dirname(__file__)

    # Create server with user extensions
    server = create_mcp_server(
        config_factory=get_user_config,
        credentials_factory=get_user_credentials,
        lifecycle=ServerLifecycle(),
        additional_module_paths=[
            (os.path.join(app_dir, "tools"), "app.tools"),
            (os.path.join(app_dir, "prompts"), "app.prompts"),
            (os.path.join(app_dir, "resources"), "app.resources"),
        ],
        transport="streamable-http",
    )

    try:
        server.run(show_banner=True)
    except KeyboardInterrupt:
        # Exit cleanly on Ctrl+C without showing traceback
        sys.exit(0)
