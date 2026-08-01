from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Configuration class for the Users application.

    Handles app initialization and signal registration.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "users"

    def ready(self) -> None:
        """Executed when the application is ready.

        Imports and registers signals to ensure they are active.
        """
        import users.signals  # noqa: F401
