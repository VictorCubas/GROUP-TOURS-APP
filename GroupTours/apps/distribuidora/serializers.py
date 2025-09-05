from rest_framework import serializers
from .models import Distribuidora

class DistribuidoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribuidora
        fields = [
            'id',
            'nombre',
            'descripcion',
            'telefono',
            'email',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
