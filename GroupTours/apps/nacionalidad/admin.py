from django.contrib import admin
from .models import Nacionalidad

@admin.register(Nacionalidad)
class NacionalidadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo_alpha2")   # columnas visibles en la lista
    search_fields = ("nombre", "codigo_alpha2")  # buscador en admin
    ordering = ("nombre",)  # orden alfabético