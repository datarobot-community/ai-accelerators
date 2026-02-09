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
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Literal, ParamSpec, TypeVar, Union


class LogLevel(str, Enum):
    ERROR = "ERROR"
    WARN = "WARNING"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


FormatType = Literal["json", "text"]


_STANDARD_LOG_RECORD_ATTRS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
)
_OTHER_LOG_RECORD_ATTRS = set({"asctime", "message", "color_message"})
_ALL_EXCLUDED_LOG_RECORD_ATTRS = _STANDARD_LOG_RECORD_ATTRS.union(
    _OTHER_LOG_RECORD_ATTRS
)


class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.
    Formats log records as JSON with standard fields like timestamp, level, and message.
    Only includes explicitly added extra parameters from the logging call.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.default_fields: Dict[
            str, Union[Callable[[logging.LogRecord], Any], Any]
        ] = {
            "timestamp": lambda _: datetime.now(timezone.utc).isoformat(),
            "level": lambda record: record.levelname,
            "logger": lambda record: record.name,
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as JSON.

        Args:
            record: The log record to format

        Returns:
            A JSON string containing:
            - timestamp: ISO format UTC timestamp
            - level: Log level name
            - logger: Logger name
            - message: The log message
            - exception: Exception details (if present)
            - Additional fields from the log record (if JSON serializable)
        """
        # Start with default fields
        log_data = {
            field: getter(record) if callable(getter) else getter
            for field, getter in self.default_fields.items()
        }

        # Add message
        log_data["message"] = record.getMessage()

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        # Include only explicitly added extra fields by filtering out standard attributes
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _ALL_EXCLUDED_LOG_RECORD_ATTRS
        }
        for key, value in extra_fields.items():
            try:
                json.dumps(value, default=str)
                log_data[key] = value
            except ValueError as e:
                log_data[key] = f"<serialization error: {str(e)}>"

        return json.dumps(log_data, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    """
    Custom text formatter that includes extra fields in the output.
    Formats log records as text with standard fields and any additional fields
    appended to the message in key=value format, separated by ' | '.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as text, including extra fields.
        """
        message = super().format(record)

        # Include only explicitly added extra fields by filtering out standard attributes
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _ALL_EXCLUDED_LOG_RECORD_ATTRS
        }
        if extra_fields:
            extra_str = " | ".join(f"{k}={v}" for k, v in extra_fields.items())
            message = f"{message} | {extra_str}"

        return message


def init_logging(
    level: LogLevel = LogLevel.INFO,
    format_type: FormatType = "text",
    stream: Any = sys.stdout,
) -> None:
    """
    Initialize the root logger globally.

    This function should be called once at the application's startup to set
    the global logging level and format. After this, any logger obtained
    via `logging.getLogger(__name__)` will inherit these settings.

    Args:
        level: The minimum logging level (e.g., logging.INFO, 'DEBUG').
        format_type: The format type to use ('json' or 'text').
        stream: The stream to write logs to (defaults to stdout).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level.value)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler with appropriate formatter
    handler = logging.StreamHandler(stream)
    if format_type == "json":
        handler.setFormatter(JsonFormatter())
    else:
        text_formatter = TextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        text_formatter.converter = time.gmtime
        handler.setFormatter(text_formatter)

    root_logger.addHandler(handler)


def get_logger(
    name: str = "agentic-application-starter",
    level: LogLevel = LogLevel.INFO,
    stream: Any = sys.stdout,
    format_type: FormatType = "text",
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: The name of the logger
        level: The logging level (can be int or string like 'INFO', 'DEBUG', etc.)
        stream: The stream to write logs to (defaults to stdout)
        format_type: The format type to use ('json' or 'text', defaults to 'text')

    Returns:
        A configured logger instance
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())

    # Create handler with appropriate formatter
    handler = logging.StreamHandler(stream)
    if format_type == "json":
        handler.setFormatter(JsonFormatter())
    else:
        text_formatter = TextFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        text_formatter.converter = time.gmtime
        handler.setFormatter(text_formatter)

    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Remove existing handlers
    for existing_handler in logger.handlers:
        logger.removeHandler(existing_handler)

    logger.addHandler(handler)
    return logger


P = ParamSpec("P")
T = TypeVar("T")


def log_api_call(
    func: Callable[P, Coroutine[Any, Any, T]],
) -> Callable[P, Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger = get_logger()
        request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        separator = f"\n{'=' * 80}\n"
        logger.info(
            f"{separator}API CALL START: {func.__name__} [{request_id}]{separator}"
        )
        try:
            result = await func(*args, **kwargs)
            logger.info(
                f"{separator}API CALL COMPLETE: {func.__name__} [{request_id}]{separator}"
            )
            return result
        except Exception as e:
            error_log = (
                f"ERROR IN API CALL [{request_id}]\n"
                "------------------------\n"
                f"Function: {func.__name__}\n"
                f"Error Type: {type(e).__name__}\n"
                f"Error Message: {str(e)}\n\n"
                "Stack Trace:\n"
            )
            logger.error(error_log, exc_info=True)
            raise

    return wrapper
