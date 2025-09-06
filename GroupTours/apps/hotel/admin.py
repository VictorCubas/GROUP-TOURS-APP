from django.contrib import admin
from .models import Hotel

@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'precio_habitacion', 'moneda', 'activo', 'fecha_creacion', 'fecha_modificacion')
    list_filter = ('activo', 'moneda')
    search_fields = ('nombre', 'moneda__nombre')
