from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration class for the Users application.

    Handles app initialization and signal registration.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "users"

    def ready(self) -> None:
        """Executed when the application is ready.

        Imports the receivers this app connects, and the system checks that
        verify what a host has to supply for the app to behave as documented.
        """
        import users.checks
        import users.signals  # noqa: F401
