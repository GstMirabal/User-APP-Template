"""Step-up authentication state (ADR-0002).

Step-up gates the two most destructive endpoints in the project: writing
encrypted secrets, and irreversible account anonymisation. It requires the
caller to have re-entered their password recently.

The grant is recorded in two places because the project accepts two
authentication styles. Session clients get it in the session, as before. Token
clients have no session at all — `request.session` exists but is never
persisted on a bearer-token request — so for them the grant lives in the shared
cache, keyed by user id. Without the second path, `PATCH /me/secrets/` and
`POST /me/anonymize/` are unreachable for every JWT client.

The cache path requires a backend shared across workers (ADR-0001); with the
per-process default it would be no more reliable than the session.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from django.core.cache import cache
from django.utils import timezone

from .defaults import step_up_window_seconds

if TYPE_CHECKING:
    from rest_framework.request import Request

SESSION_KEY = "step_up_timestamp"
CACHE_KEY_TEMPLATE = "step_up:{user_id}"


def _window() -> timedelta:
    """Returns the configured step-up validity window."""
    return timedelta(seconds=step_up_window_seconds())


def _cache_key(user_id: Any) -> str:
    """Builds the cache key holding a user's step-up grant.

    Args:
        user_id (Any): Primary key of the user.

    Returns:
        str: The namespaced cache key.
    """
    return CACHE_KEY_TEMPLATE.format(user_id=user_id)


def _is_fresh(raw_timestamp: str | None) -> bool:
    """Reports whether an ISO timestamp falls inside the step-up window.

    Args:
        raw_timestamp (str | None): ISO-8601 timestamp, or None when absent.

    Returns:
        bool: True when the timestamp is present, parseable and recent.
    """
    if not raw_timestamp:
        return False

    try:
        granted_at = timezone.datetime.fromisoformat(raw_timestamp)
    except (TypeError, ValueError):
        return False

    if timezone.is_naive(granted_at):
        granted_at = timezone.make_aware(granted_at)

    return timezone.now() <= granted_at + _window()


def _has_live_session(request: Request) -> bool:
    """Reports whether the request carries an already-established session.

    A bearer-token request still exposes `request.session`, but it is an empty
    unsaved object with no `session_key`. Writing to it would make the response
    set a session cookie, quietly turning a stateless client into a stateful
    one and creating a session record per re-authentication.

    Args:
        request (Request): The request being inspected.

    Returns:
        bool: True only for a genuine, already-persisted session.
    """
    session = getattr(request, "session", None)
    return session is not None and bool(getattr(session, "session_key", None))


def grant(request: Request, user: Any) -> str:
    """Records a successful re-authentication for the given user.

    The cache is always written, since it is the backend that serves token
    clients. The session is written only when one already exists — see
    `_has_live_session`.

    Args:
        request (Request): The re-authentication request.
        user (Any): The user who just proved possession of their password.

    Returns:
        str: The ISO timestamp recorded.
    """
    now = timezone.now().isoformat()

    if _has_live_session(request):
        request.session[SESSION_KEY] = now

    cache.set(_cache_key(user.pk), now, timeout=step_up_window_seconds())
    return now


def is_granted(request: Request, user: Any) -> bool:
    """Reports whether the user currently holds a valid step-up grant.

    The timestamp is re-validated even for the cache path, whose TTL would
    already have expired it. Shortening ``STEP_UP_WINDOW_SECONDS`` therefore
    takes effect immediately instead of only applying to new grants.

    Args:
        request (Request): The request being authorised.
        user (Any): The authenticated user.

    Returns:
        bool: True when either backend holds a fresh grant.
    """
    session = getattr(request, "session", None)
    if session is not None and _is_fresh(session.get(SESSION_KEY)):
        return True

    return _is_fresh(cache.get(_cache_key(user.pk)))


def revoke(request: Request, user: Any) -> None:
    """Clears the step-up grant from both backends.

    Args:
        request (Request): The current request.
        user (Any): The user whose grant is being dropped.
    """
    session = getattr(request, "session", None)
    if session is not None:
        session.pop(SESSION_KEY, None)

    cache.delete(_cache_key(user.pk))
