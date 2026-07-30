"""UTC-normalised structured logging.

Part of the settings package. See `config/settings/__init__.py` for the load
order and why the split exists.
"""

import datetime
import logging
from datetime import UTC
from pathlib import Path
from typing import override

from django.core.exceptions import ImproperlyConfigured

from .third_party import *

# SECTION 11: PROFESSIONAL LOGGING CONFIGURATION
# ==============================================================================
# Production-ready logging setup, adaptable to different environments.
# https://docs.djangoproject.com/en/5.2/topics/logging/
# ------------------------------------------------------------------------------


class UTCFormatter(logging.Formatter):
    """Custom logging formatter to ensure all timestamps are in UTC.

    Follows the ISO 8601 standard for unambiguous logging across environments.
    """

    @override
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Runs the time formatting logic.

        Args:
            record (logging.LogRecord): The log record instance.
            datefmt (Optional[str]): The format string for the timestamp.

        Returns:
            str: The ISO 8601 formatted timestamp in UTC.
        """
        dt = datetime.datetime.fromtimestamp(record.created, tz=UTC)
        return dt.strftime(datefmt or "%Y-%m-%dT%H:%M:%SZ")


try:
    logs_dir_str = config["project_logging"].get("PROJECT_LOGS_DIR")
    if logs_dir_str:
        logs_dir = Path(logs_dir_str)
        logs_dir.mkdir(parents=True, exist_ok=True)
    else:
        raise ValueError("PROJECT_LOGS_DIR is not defined in config.toml")
except (KeyError, ValueError) as e:
    raise ImproperlyConfigured(f"Logging directory setup failed. Error: {e}") from e


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} [{name}] {message}", "style": "{"},
        "verbose": {
            "()": UTCFormatter,
            "format": "{levelname} {asctime} {module} [{funcName}:{lineno}] {message}",
            "style": "{",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(lineno)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "project_log_file": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": logs_dir / "project.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "project_json_file": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": logs_dir / "project.json",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "project_log_file", "project_json_file"],
            "level": "DEBUG" if DEBUG else "WARNING",
            "propagate": False,
        },
        "project": {
            "handlers": ["console", "project_log_file", "project_json_file"],
            "level": "DEBUG",
            "propagate": False,
        },
        # Application code calls logging.getLogger(__name__), which yields
        # "apps.*" and "utils.*". Without these two entries those records
        # reach no handler at all and are discarded silently — including the
        # decryption-failure CRITICAL and the TOTP replay warning.
        "apps": {
            "handlers": ["console", "project_log_file", "project_json_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "utils": {
            "handlers": ["console", "project_log_file", "project_json_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
# ------------------------------------------------------------------------------
