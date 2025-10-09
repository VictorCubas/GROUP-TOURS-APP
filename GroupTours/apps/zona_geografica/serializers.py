from rest_framework import serializers
from .models import ZonaGeografica

class ZonaGeograficaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZonaGeografica
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activo",
            "en_uso",
            "fecha_creacion",
            "fecha_modificacion",
        ]
        read_only_fields = ["fecha_creacion", "fecha_modificacion"]
