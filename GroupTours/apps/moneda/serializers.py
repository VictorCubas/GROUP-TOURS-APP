from rest_framework import serializers
from .models import Moneda

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id', 'nombre', 'simbolo', 'codigo', 'activo', 'fecha_creacion', 'fecha_modificacion']
