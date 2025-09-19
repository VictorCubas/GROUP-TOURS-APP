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
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'hotel']

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
    habitaciones = HabitacionSerializer(many=True)

    # Escritura: ids de los servicios del hotel
    servicios = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Servicio.objects.filter(tipo='hotel', activo=True)
    )
    # Lectura: id y nombre de cada servicio
    servicios_detalle = ServicioSimpleSerializer(
        many=True,
        source='servicios',
        read_only=True
    )

    class Meta:
        model = Hotel
        fields = [
            'id', 'nombre', 'descripcion', 'activo',
            'estrellas', 'direccion', 'ciudad', 'ciudad_nombre',
            'pais_nombre', 'cadena', 'cadena_nombre',
            'servicios',          # ids para escritura
            'servicios_detalle',  # id y nombre para lectura
            'habitaciones',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']

    # ---- MÉTODOS PERSONALIZADOS ----
    def create(self, validated_data):
        habitaciones_data = validated_data.pop('habitaciones', [])
        servicios = validated_data.pop('servicios', [])
        hotel = Hotel.objects.create(**validated_data)
        hotel.servicios.set(servicios)
        for hab in habitaciones_data:
            servicios_hab = hab.pop('servicios', [])
            habitacion = Habitacion.objects.create(hotel=hotel, **hab)
            habitacion.servicios.set(servicios_hab)
        return hotel

    def update(self, instance, validated_data):
        habitaciones_data = validated_data.pop('habitaciones', [])
        servicios = validated_data.pop('servicios', [])

        # Actualiza campos simples del hotel
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualiza servicios ManyToMany
        instance.servicios.set(servicios)

        # Política: reemplaza habitaciones existentes
        instance.habitaciones.all().delete()
        for hab in habitaciones_data:
            servicios_hab = hab.pop('servicios', [])
            habitacion = Habitacion.objects.create(hotel=instance, **hab)
            habitacion.servicios.set(servicios_hab)

        return instance

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'hotel':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Hoteles."
                )
        return value
