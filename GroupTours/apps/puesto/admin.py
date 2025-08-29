# apps/puesto/admin.py
from django.contrib import admin
from .models import Puesto

@admin.register(Puesto)
class PuestoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion')
    list_filter = ('activo', 'en_uso', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion')
    ordering = ('nombre',)
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    fieldsets = (
        (None, {
            'fields': ('nombre', 'descripcion')
        }),
        ('Estado', {
            'fields': ('activo', 'en_uso')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_modificacion')
        }),
    )
