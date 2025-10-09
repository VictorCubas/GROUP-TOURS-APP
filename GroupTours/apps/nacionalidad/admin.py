from django.contrib import admin
from .models import Nacionalidad

@admin.register(Nacionalidad)
class NacionalidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_alpha2", "zona_geografica", "activo", "en_uso")
    list_filter = ("zona_geografica", "activo", "en_uso")
    search_fields = ("nombre", "codigo_alpha2")
    ordering = ("nombre",)