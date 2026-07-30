"""Tests for the health-check endpoint.

The endpoint previously passed ``status_code=`` to DRF's ``Response``, which
accepts no such keyword, so every request raised ``TypeError`` — including the
fully healthy path. These tests pin both the healthy response and each
degraded branch.
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_health_check_reports_healthy(client) -> None:
    """All dependencies reachable yields 200 and a HEALTHY verdict."""
    response = client.get(reverse("health-check"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "database": "OK",
        "cache": "OK",
        "system": "HEALTHY",
    }


@pytest.mark.django_db
def test_health_check_reports_database_down(client, monkeypatch) -> None:
    """An unreachable database degrades the verdict and returns 503."""

    def _explode(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(
        "apps.core.views.connections",
        {"default": type("Conn", (), {"cursor": _explode})()},
    )

    response = client.get(reverse("health-check"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["database"] == "DOWN"
    assert body["cache"] == "OK"
    assert body["system"] == "DEGRADED"


@pytest.mark.django_db
def test_health_check_reports_cache_down(client, monkeypatch) -> None:
    """A cache that fails its round-trip degrades the verdict and returns 503.

    Only the view's own reference is replaced. Patching the shared cache would
    also break DRF's throttle bookkeeping, which reads the same object.
    """

    class _DeadCache:
        def set(self, *args, **kwargs) -> None:
            raise ConnectionError("cache backend unreachable")

        def get(self, *args, **kwargs) -> None:
            return None

    monkeypatch.setattr("apps.core.views.cache", _DeadCache())

    response = client.get(reverse("health-check"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["cache"] == "DOWN"
    assert body["database"] == "OK"
    assert body["system"] == "DEGRADED"
