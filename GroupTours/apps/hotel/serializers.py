from rest_framework import serializers
from .models import Hotel

class HotelSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id',
            'nombre',
            'descripcion',
            'activo',
            'precio_habitacion',
            'moneda',
            'moneda_nombre',
            'moneda_codigo',
            'fecha_creacion',
            'fecha_modificacion'
        ]
