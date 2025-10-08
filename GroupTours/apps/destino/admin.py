from django.contrib import admin
from .models import Destino

@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre_destino',
        'ciudad',
        'pais',                 # se muestra el país derivado de ciudad.pais
        'zona_geografica',
        'activo',
        'en_uso',
        'fecha_creacion',
        'fecha_modificacion',
    )
    list_filter = (
        'activo',
        'en_uso',
        'fecha_creacion',
        'ciudad__pais',         # filtrado por país a través de la ciudad
        'ciudad',
        'ciudad__pais__zona_geografica',
    )
    search_fields = (
        'descripcion',
        'ciudad__nombre',
        'ciudad__pais__nombre',
        'ciudad__pais__zona_geografica__nombre',  # 🔹 búsqueda por zona
        'hoteles__nombre',
    )
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    ordering = ('ciudad__nombre',)

    @admin.display(description="Nombre del destino")
    def nombre_destino(self, obj):
        return obj.ciudad.nombre

    @admin.display(description="País")
    def pais(self, obj):
        return obj.ciudad.pais.nombre

    @admin.display(description="Zona Geográfica")
    def zona_geografica(self, obj):
        return obj.zona_geografica.nombre if obj.zona_geografica else None
