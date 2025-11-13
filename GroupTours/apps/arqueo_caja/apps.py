from django.apps import AppConfig


class ArqueoCajaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.arqueo_caja'
    verbose_name = 'Arqueo de Caja'

    def ready(self):
        import apps.arqueo_caja.signals
