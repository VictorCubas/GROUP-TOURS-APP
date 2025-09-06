from django.contrib import admin
from .models import Destino

@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'pais', 'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion')
    list_filter = ('activo', 'en_uso', 'fecha_creacion', 'pais')
    search_fields = ('nombre', 'descripcion', 'pais__nombre', 'hoteles__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    ordering = ('nombre',)
