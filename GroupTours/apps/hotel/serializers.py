from rest_framework import serializers
from .models import Hotel

class HotelSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)
    ciudad_nombre = serializers.CharField(source='ciudad.nombre', read_only=True)
    pais_nombre = serializers.CharField(source='ciudad.pais.nombre', read_only=True)

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
            'ciudad',
            'ciudad_nombre',
            'pais_nombre',
            'fecha_creacion',
            'fecha_modificacion'
        ]
