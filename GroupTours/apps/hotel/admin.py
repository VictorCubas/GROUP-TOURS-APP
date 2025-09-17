from django.contrib import admin
from .models import Hotel

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre',
        'ciudad',
        'get_pais',
        'precio_habitacion',
        'moneda',
        'activo',
        'fecha_creacion',
        'fecha_modificacion'
    )
    list_filter = ('activo', 'moneda', 'ciudad__pais')
    search_fields = ('nombre', 'ciudad__nombre', 'ciudad__pais__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    def get_pais(self, obj):
        return obj.ciudad.pais.nombre
    get_pais.short_description = 'País'
