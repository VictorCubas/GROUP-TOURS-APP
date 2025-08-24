from rest_framework import serializers
from .models import TipoRemuneracion

class TipoRemuneracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoRemuneracion
        fields = [
            'id',
            'nombre',
            'descripcion',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
