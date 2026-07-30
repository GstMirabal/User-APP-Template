import logging

from django.core.cache import cache
from django.db import connections
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Health check probing the critical dependencies of the service.

    Each dependency is probed independently, so one failing subsystem degrades
    the response without masking the status of the other.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        """Reports the liveness of the database and the cache backend.

        Args:
            request (Request): The incoming request. Unused; the probe takes no
                parameters.

        Returns:
            Response: A status map for each dependency plus an aggregate
                ``system`` verdict. ``200`` when every probe succeeds, ``503``
                as soon as one fails.
        """
        report: dict[str, str] = {
            "database": "OK",
            "cache": "OK",
            "system": "HEALTHY",
        }
        status_code: int = http_status.HTTP_200_OK

        try:
            connections["default"].cursor()
        except Exception as exc:  # any driver-level error means DOWN
            logger.error("HealthCheck: database is DOWN: %s", exc)
            report["database"] = "DOWN"
            report["system"] = "DEGRADED"
            status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE

        try:
            cache.set("health_check", "alive", timeout=5)
            if not cache.get("health_check"):
                raise ValueError("cache set/get round-trip failed")
        except Exception as exc:  # any backend-level error means DOWN
            logger.error("HealthCheck: cache is DOWN: %s", exc)
            report["cache"] = "DOWN"
            report["system"] = "DEGRADED"
            status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(report, status=status_code)
