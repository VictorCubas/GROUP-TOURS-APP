from rest_framework import serializers
from .models import Modulo

class ModuloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Modulo
        fields = ['id', 'nombre', 'descripcion', 'activo', 'fecha_creacion', 'fecha_modificacion',]