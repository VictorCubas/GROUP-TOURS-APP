# apps/ubicaciones/serializers.py
from rest_framework import serializers
from .models import Ciudad

class CiudadSerializer(serializers.ModelSerializer):
    pais_nombre = serializers.CharField(source='pais.nombre', read_only=True)

    class Meta:
        model = Ciudad
        fields = [
            'id', 'nombre', 'pais', 'pais_nombre',
            'activo', 'fecha_creacion', 'fecha_modificacion'
        ]
