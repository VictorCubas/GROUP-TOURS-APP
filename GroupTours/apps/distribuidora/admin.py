from django.contrib import admin
from .models import Distribuidora

@admin.register(Distribuidora)
class DistribuidoraAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'telefono', 'email', 'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion')
    list_filter = ('activo', 'en_uso', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion', 'telefono', 'email')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    ordering = ('nombre',)
