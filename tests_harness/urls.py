"""URL configuration for the test harness.

Mounts the app the way a host project would, at the prefix the contract
documents.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/users/", include("users.urls")),
]
