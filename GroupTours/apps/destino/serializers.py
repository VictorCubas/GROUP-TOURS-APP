from rest_framework import serializers
from .models import Destino
from apps.hotel.serializers import HotelSerializer

from apps.nacionalidad.models import Nacionalidad

class NacionalidadSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nacionalidad
        fields = ["id", "nombre"]


class DestinoSerializer(serializers.ModelSerializer):
    # Solo lectura para mostrar detalle del país
    pais = NacionalidadSimpleSerializer(read_only=True)

    # Solo escritura para asignar el país por ID
    pais_id = serializers.PrimaryKeyRelatedField(
        queryset=Nacionalidad.objects.all(),
        source="pais",
        write_only=True
    )

    hoteles = HotelSerializer(many=True, read_only=True)
    hoteles_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Destino.hoteles.field.related_model.objects.all(),
        source='hoteles'
    )

    class Meta:
        model = Destino
        fields = [
            'id',
            'nombre',
            'descripcion',
            'pais',         # Lectura
            'pais_id',      # Escritura
            'hoteles',
            'hoteles_ids',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']