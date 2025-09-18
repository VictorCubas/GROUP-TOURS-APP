from rest_framework import serializers
from .models import CadenaHotelera, Hotel, Habitacion, Servicio

# -------------------- CADENA HOTELERA --------------------
class CadenaHoteleraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CadenaHotelera
        fields = "__all__"


# -------------------- HABITACION --------------------
class HabitacionSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)

    class Meta:
        model = Habitacion
        fields = [
            'id', 'hotel', 'numero', 'tipo', 'capacidad',
            'precio_noche', 'moneda', 'moneda_nombre', 'servicios', 'activo',
            'fecha_creacion', 'fecha_modificacion'
        ]

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'habitacion':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Habitaciones."
                )
        return value


# -------------------- HOTEL --------------------
class HotelSerializer(serializers.ModelSerializer):
    cadena_nombre = serializers.CharField(source='cadena.nombre', read_only=True)
    ciudad_nombre = serializers.CharField(source='ciudad.nombre', read_only=True)
    pais_nombre = serializers.CharField(source='ciudad.pais.nombre', read_only=True)
    habitaciones = HabitacionSerializer(many=True, read_only=True)

    class Meta:
        model = Hotel
        fields = [
            'id', 'nombre', 'descripcion', 'activo',
            'estrellas', 'direccion', 'ciudad', 'ciudad_nombre', 'pais_nombre',
            'cadena', 'cadena_nombre', 'servicios',
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


# -------------------- SERVICIO --------------------
class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ['id', 'nombre', 'descripcion', 'tipo', 'activo', 'fecha_creacion', 'fecha_modificacion']
