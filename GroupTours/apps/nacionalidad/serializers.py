from rest_framework import serializers

from apps.zona_geografica.models import ZonaGeografica
from .models import Nacionalidad

class ZonaGeograficaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZonaGeografica
        fields = ["id", "nombre"]


class NacionalidadSerializer(serializers.ModelSerializer):
    zona_geografica = ZonaGeograficaSimpleSerializer(read_only=True)
    zona_geografica_id = serializers.PrimaryKeyRelatedField(
        queryset=ZonaGeografica.objects.all(),
        source="zona_geografica",
        write_only=True,
        required=False
    )

    class Meta:
        model = Nacionalidad
        fields = [
            "id",
            "nombre",
            "codigo_alpha2",
            "zona_geografica",       # lectura
            "zona_geografica_id",    # escritura
            "activo",
            "en_uso",
            "fecha_creacion",
            "fecha_modificacion",
        ]