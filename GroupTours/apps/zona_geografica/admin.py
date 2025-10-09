from django.contrib import admin
from .models import ZonaGeografica


@admin.register(ZonaGeografica)
class ZonaGeograficaAdmin(admin.ModelAdmin):
    """
    Configuración del panel de administración para las Zonas Geográficas.
    """
    list_display = (
        "nombre",
        "activo",
        "en_uso",
        "fecha_creacion",
        "fecha_modificacion",
    )
    list_filter = ("activo", "en_uso", "fecha_creacion")
    search_fields = ("nombre", "descripcion")
    ordering = ("-fecha_creacion",)
    readonly_fields = ("fecha_creacion", "fecha_modificacion")

    fieldsets = (
        ("Información General", {
            "fields": ("nombre", "descripcion")
        }),
        ("Estado", {
            "fields": ("activo", "en_uso")
        }),
        ("Fechas", {
            "fields": ("fecha_creacion", "fecha_modificacion"),
            "classes": ("collapse",)
        }),
    )

    def get_queryset(self, request):
        """
        Optimiza el queryset base para mejorar el rendimiento en list_display.
        """
        qs = super().get_queryset(request)
        return qs.only("id", "nombre", "activo", "en_uso", "fecha_creacion", "fecha_modificacion")
