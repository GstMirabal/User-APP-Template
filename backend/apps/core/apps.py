from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration class for the Core application.

    Handles app initialization and registration of the project's custom
    system checks.
    """

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.core"

    def ready(self) -> None:
        """Executed when the application is ready.

        Imports the custom system checks so their ``@register`` decorators run.
        """
        import apps.core.checks  # noqa: F401
