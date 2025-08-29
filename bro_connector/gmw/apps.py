from django.apps import AppConfig


class GmwAanleveringConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gmw"
    verbose_name = "GMW"

    def ready(self):
        import gmw.signals
