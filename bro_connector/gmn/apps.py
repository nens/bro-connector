from django.apps import AppConfig


class GmnAanleveringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gmn"
    verbose_name = "GMN"

    def ready(self):
        import gmn.signals  # noqa: F401
