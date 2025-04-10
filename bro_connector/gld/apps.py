from django.apps import AppConfig


class GldAanleveringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gld"
    verbose_name = "GLD"

    def ready(self) -> None:
        import gld.signals  # noqa: F401
