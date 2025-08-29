from rest_framework import serializers
from .models import Puesto

class PuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puesto
        fields = ['id', 'nombre', 'descripcion', 'en_uso',  'activo', 'fecha_creacion', 'fecha_modificacion',]
