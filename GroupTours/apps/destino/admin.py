from django.contrib import admin
from .models import Destino

@admin.register(Destino)
class DestinoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nombre_destino',
        'ciudad',
        'pais',                 # se muestra el país derivado de ciudad.pais
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
    )
    search_fields = (
        'descripcion',
        'ciudad__nombre',
        'ciudad__pais__nombre',
        'hoteles__nombre',
    )
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')
    ordering = ('ciudad__nombre',)

    @admin.display(description="Nombre del destino")
    def nombre_destino(self, obj):
        """
        Si no tienes un campo 'nombre' propio y solo usas la ciudad
        como nombre de destino, mostramos el nombre de la ciudad.
        """
        return obj.ciudad.nombre

    @admin.display(description="País")
    def pais(self, obj):
        """
        Muestra el país de la ciudad asociada.
        """
        return obj.ciudad.pais.nombre
