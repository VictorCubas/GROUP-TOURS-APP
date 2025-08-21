from rest_framework import serializers
from .models import Nacionalidad

class NacionalidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nacionalidad
        fields = ['id', 'nombre', 'codigo_alpha2', 'activo', 'fecha_creacion', 'fecha_modificacion',]
