from rest_framework import serializers
from .models import TipoPaquete

class TipoPaqueteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPaquete
        fields = ['id', 'nombre', 'descripcion', 'activo', 'fecha_creacion', 'fecha_modificacion']
