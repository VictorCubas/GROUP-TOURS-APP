from django.contrib import admin
from .models import TipoCostoSalida


@admin.register(TipoCostoSalida)
class TipoCostoSalidaAdmin(admin.ModelAdmin):
    list_display = ["codigo", "nombre", "dividir_por_pasajeros", "activo"]
    list_filter = ["activo", "dividir_por_pasajeros"]
    search_fields = ["codigo", "nombre"]
    ordering = ["nombre"]
