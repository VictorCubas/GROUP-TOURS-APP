# apps/ubicaciones/admin.py
from django.contrib import admin
from .models import Ciudad

@admin.register(Ciudad)
class CiudadAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'pais', 'activo', 'en_uso',
                    'fecha_creacion', 'fecha_modificacion']
    list_filter = ['activo', 'en_uso', 'pais']
    search_fields = ['nombre', 'pais__nombre']
    ordering = ['nombre']
