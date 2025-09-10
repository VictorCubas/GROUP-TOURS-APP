from django.contrib import admin
from .models import Moneda

@admin.register(Moneda)
class MonedaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'codigo', 'simbolo', 'activo', 'fecha_creacion', 'fecha_modificacion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo')
