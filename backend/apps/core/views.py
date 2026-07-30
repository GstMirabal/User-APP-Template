import logging

from django.core.cache import cache
from django.db import connections
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Industrial-grade health check to ensure critical dependencies are alive.
    Checks: Database (PostgreSQL) and Cache (Redis).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        status = {"database": "OK", "cache": "OK", "system": "HEALTHY"}
        status_code = 200

        # 1. Check Database
        try:
            connections["default"].cursor()
        except Exception as e:
            logger.error("HealthCheck: Database is DOWN: %s", e)
            status["database"] = "DOWN"
            status["system"] = "DEGRADED"
            status_code = 503

        # 2. Check Cache (Redis)
        try:
            cache.set("health_check", "alive", timeout=5)
            if not cache.get("health_check"):
                raise ValueError("Cache set/get failed")
        except Exception as e:
            logger.error("HealthCheck: Cache is DOWN: %s", e)
            status["cache"] = "DOWN"
            status["system"] = "DEGRADED"
            status_code = 503

        return Response(status, status_code=status_code)
