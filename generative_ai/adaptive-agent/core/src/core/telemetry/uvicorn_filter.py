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

from .logging import JsonFormatter, TextFormatter


class HealthCheckFilter(logging.Filter):
    """Filter out health check requests from access logs."""

    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        self.log_level = log_level

    def filter(self, record: logging.LogRecord) -> bool:
        numeric_log_level = getattr(logging, self.log_level.upper())
        # Filter out health check requests only when log level is INFO or higher
        if numeric_log_level <= logging.DEBUG:
            return True

        if hasattr(record, "getMessage"):
            message = record.getMessage()
            if "/health" in message and "GET" in message:
                return False
        return True


def configure_uvicorn_logging(
    log_format: str = "text", log_level: str = "INFO"
) -> None:
    """Configure uvicorn logging to use our custom formatter and filter."""

    # Configure uvicorn access logger
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            TextFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    # Add the health check filter
    handler.addFilter(HealthCheckFilter(log_level))

    access_logger.addHandler(handler)
    access_logger.setLevel(getattr(logging, log_level.upper()))
    access_logger.propagate = False

    # Configure uvicorn error logger
    error_logger = logging.getLogger("uvicorn.error")
    error_logger.handlers.clear()

    handler = logging.StreamHandler()
    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            TextFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    error_logger.addHandler(handler)
    error_logger.setLevel(getattr(logging, log_level.upper()))
    error_logger.propagate = False
