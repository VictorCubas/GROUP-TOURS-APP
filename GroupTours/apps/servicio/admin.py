from django.contrib import admin
from .models import Servicio

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre', 'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion']
    list_filter = ['activo', 'en_uso']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
