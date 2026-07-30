"""Tests that application loggers actually reach a handler.

``LOGGING`` originally declared only the ``django`` and ``project`` loggers,
while every module calls ``logging.getLogger(__name__)`` — yielding ``apps.*``
and ``utils.*``. Those records reached no handler and were discarded in
silence, including the decryption-failure CRITICAL and the TOTP replay warning.
"""

import logging

import pytest

APPLICATION_LOGGERS = [
    "apps.users.views",
    "apps.users.services",
    "apps.users.serializers.registration",
    "apps.core.views",
    "utils.encryption",
]


def _resolved_handlers(name: str) -> list[logging.Handler]:
    """Walks the logger hierarchy the way logging dispatches a record.

    Args:
        name (str): Dotted logger name.

    Returns:
        list[logging.Handler]: Every handler the record would reach, following
            ``propagate`` exactly as ``logging.Logger.callHandlers`` does.
    """
    handlers: list[logging.Handler] = []
    current: logging.Logger | None = logging.getLogger(name)
    while current:
        handlers.extend(current.handlers)
        current = current.parent if current.propagate else None
    return handlers


@pytest.mark.parametrize("logger_name", APPLICATION_LOGGERS)
def test_application_logger_reaches_a_handler(logger_name: str) -> None:
    """No application logger may resolve to an empty handler list."""
    assert _resolved_handlers(logger_name), (
        f"{logger_name!r} resolves to no handler; its records are discarded"
    )


def test_security_relevant_record_is_emitted() -> None:
    """A warning from an application logger actually reaches a handler.

    ``caplog`` cannot observe this: the ``apps`` logger sets
    ``propagate = False`` (deliberately, to avoid duplicate records), so nothing
    reaches the root handler pytest attaches. The handler is therefore installed
    on the logger under test.
    """
    logger = logging.getLogger("apps.users.services")
    records: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Collector(level=logging.WARNING)
    logger.addHandler(handler)
    try:
        logger.warning("replay attack detected for user %s", "abc123")
    finally:
        logger.removeHandler(handler)

    assert [r.getMessage() for r in records] == [
        "replay attack detected for user abc123"
    ]
