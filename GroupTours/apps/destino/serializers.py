from rest_framework import serializers
from .models import Destino

class DestinoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Destino
        fields = [
            'id',
            'nombre',
            'descripcion',
            'pais',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
