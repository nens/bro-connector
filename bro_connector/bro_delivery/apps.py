from django.apps import AppConfig


class BroDeliveryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bro_delivery"
    verbose_name = "BRO Berichtenoverzicht"

    def ready(self):
        import bro_delivery.signals  # noqa: F401
