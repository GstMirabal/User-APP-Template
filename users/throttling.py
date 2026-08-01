"""Throttling for the endpoints that hand out or check credentials.

DRF's `ScopedRateThrottle` reads its rate from
`REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]` and raises `ImproperlyConfigured`
when the scope is absent — as a `500`, on the first request that reaches the
endpoint, so a host learns about it from a user rather than from a test.

That is what happened when this app was first vendored into a real project:
registration, verification and re-authentication all returned `500`, while the
app's own suite stayed green because its test harness happened to declare the
rate. A reusable app cannot depend on a host having read a table.

So the rate is supplied here, and a host that wants a different one sets
`DEFAULT_THROTTLE_RATES["sensitive"]` as usual — that still wins.
"""

from rest_framework.throttling import ScopedRateThrottle

from .defaults import sensitive_throttle_rate


class SensitiveScopedRateThrottle(ScopedRateThrottle):
    """A scoped throttle that falls back to this app's own rate.

    Behaves exactly like `ScopedRateThrottle` when the host declares the scope.
    """

    def get_rate(self) -> str:
        """Return the configured rate, or this app's default.

        Returns:
            str: A DRF rate string such as `"5/minute"`.
        """
        scope = getattr(self, "scope", None)
        rates = getattr(self, "THROTTLE_RATES", {}) or {}
        if scope and scope in rates:
            return rates[scope]
        return sensitive_throttle_rate()
