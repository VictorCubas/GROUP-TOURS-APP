from rest_framework import serializers
from .models import Destino
from apps.hotel.serializers import HotelSerializer
from apps.ciudad.models import Ciudad

class CiudadSimpleSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.CharField(source="pais.nombre", read_only=True)
    pais_id = serializers.CharField(source="pais.id", read_only=True)

    class Meta:
        model = Ciudad
        fields = ["id", "nombre", "pais_nombre", "pais_id"]

class DestinoSerializer(serializers.ModelSerializer):
    ciudad = CiudadSimpleSerializer(read_only=True)
    ciudad_id = serializers.PrimaryKeyRelatedField(
        queryset=Ciudad.objects.all(),
        source="ciudad",
        write_only=True
    )
    hoteles = HotelSerializer(many=True, read_only=True)
    hoteles_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Destino.hoteles.field.related_model.objects.all(),
        source="hoteles"
    )

    class Meta:
        model = Destino
        fields = [
            "id",
            "ciudad",        # lectura
            "ciudad_id",     # escritura
            "descripcion",
            "hoteles",
            "hoteles_ids",
            "activo",
            "en_uso",
            "fecha_creacion",
            "fecha_modificacion",
        ]
        read_only_fields = ["fecha_creacion", "fecha_modificacion"]
