from .models import CadenaHotelera, Hotel, Habitacion, Servicio
from rest_framework import serializers

class CadenaHoteleraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CadenaHotelera
        fields = "__all__"

class ServicioSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple para mostrar id y nombre del servicio."""
    class Meta:
        model = Servicio
        fields = ['id', 'nombre']


class HabitacionSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)

    class Meta:
        model = Habitacion
        fields = [
            'id', 'hotel', 'numero', 'tipo', 'capacidad',
            'precio_noche', 'moneda', 'moneda_nombre', 'servicios',
            'activo', 'fecha_creacion', 'fecha_modificacion'
        ]

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'habitacion':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Habitaciones."
                )
        return value


class HotelSerializer(serializers.ModelSerializer):
    cadena_nombre = serializers.CharField(source='cadena.nombre', read_only=True)
    ciudad_nombre = serializers.CharField(source='ciudad.nombre', read_only=True)
    pais_nombre = serializers.CharField(source='ciudad.pais.nombre', read_only=True)
    habitaciones = HabitacionSerializer(many=True, read_only=True)

    # 🔑 Aquí cambiamos el campo servicios para que use el serializer simple
    servicios = ServicioSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id', 'nombre', 'descripcion', 'activo',
            'estrellas', 'direccion', 'ciudad', 'ciudad_nombre',
            'pais_nombre', 'cadena', 'cadena_nombre',
            'servicios',               # ahora devuelve objetos con id y nombre
            'habitaciones',
            'fecha_creacion', 'fecha_modificacion'
        ]

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'hotel':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Hoteles."
                )
        return value
