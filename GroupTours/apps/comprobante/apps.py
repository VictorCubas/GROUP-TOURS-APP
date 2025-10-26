from django.apps import AppConfig


class ComprobanteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.comprobante'
    verbose_name = 'Comprobantes y Documentación'

    def ready(self):
        import apps.comprobante.signals
