from rest_framework import serializers
from .models import Reserva, Pasajero, ReservaServiciosAdicionales
from apps.persona.models import PersonaFisica
from apps.paquete.models import SalidaPaquete
from apps.paquete.serializers import PaqueteSerializer
from apps.hotel.models import Hotel, Habitacion
from apps.servicio.models import Servicio


class PersonaFisicaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonaFisica
        fields = ["id", "nombre", "apellido", "documento", "email", "telefono"]


class SalidaPaqueteSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalidaPaquete
        fields = ["id", "fecha_salida", "fecha_regreso", "precio_actual", "precio_final", "senia"]


class HotelSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hotel
        fields = ["id", "nombre", "direccion", "estrellas"]


class HabitacionSimpleSerializer(serializers.ModelSerializer):
    hotel_nombre = serializers.CharField(source="hotel.nombre", read_only=True)

    class Meta:
        model = Habitacion
        fields = ["id", "numero", "tipo", "capacidad", "precio_noche", "hotel_nombre"]


class PasajeroSerializer(serializers.ModelSerializer):
    persona = PersonaFisicaSimpleSerializer(read_only=True)

    class Meta:
        model = Pasajero
        fields = [
            "id",
            "persona",
            "es_titular",
            "ticket_numero",
            "voucher_codigo",
            "fecha_registro",
        ]


class PasajeroCreateSerializer(serializers.Serializer):
    """
    Serializer simple para asociar personas existentes a una reserva como pasajeros.
    Solo requiere el persona_id.
    """
    persona_id = serializers.IntegerField()

    def validate_persona_id(self, value):
        """Validar que la persona existe"""
        if not PersonaFisica.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"No existe una PersonaFisica con id={value}")
        return value


class ReservaSerializer(serializers.ModelSerializer):
    titular = PersonaFisicaSimpleSerializer(read_only=True)
    pasajeros = PasajeroSerializer(many=True, read_only=True)
    paquete = PaqueteSerializer(read_only=True)
    salida = SalidaPaqueteSimpleSerializer(read_only=True)
    hotel = HotelSimpleSerializer(read_only=True)  # Calculado desde habitacion.hotel
    habitacion = HabitacionSimpleSerializer(read_only=True)

    # Write-only fields
    titular_id = serializers.PrimaryKeyRelatedField(
        queryset=PersonaFisica.objects.all(),
        write_only=True,
        source="titular",
        required=False,
        allow_null=True
    )
    paquete_id = serializers.PrimaryKeyRelatedField(
        queryset=Reserva.objects.model.paquete.field.related_model.objects.all(),
        write_only=True,
        source="paquete"
    )
    salida_id = serializers.PrimaryKeyRelatedField(
        queryset=SalidaPaquete.objects.all(),
        write_only=True,
        source="salida",
        required=False,
        allow_null=True
    )
    habitacion_id = serializers.PrimaryKeyRelatedField(
        queryset=Habitacion.objects.all(),
        write_only=True,
        source="habitacion",
        required=False
    )

    # Pasajeros como campo write-only para creación
    pasajeros_data = PasajeroCreateSerializer(many=True, write_only=True, required=False)

    # Campos calculados
    precio_base_paquete = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Precio unitario por pasajero (habitación + ganancia + servicios base)"
    )
    costo_total_estimado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Costo total de la reserva (precio_unitario × cantidad + servicios adicionales)"
    )
    seña_total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Seña total requerida según cantidad de pasajeros"
    )

    class Meta:
        model = Reserva
        fields = [
            "id",
            "codigo",
            "observacion",
            "titular",
            "titular_id",
            "paquete",
            "paquete_id",
            "salida",
            "salida_id",
            "hotel",  # Read-only, calculado desde habitacion.hotel
            "habitacion",
            "habitacion_id",
            "fecha_reserva",
            "cantidad_pasajeros",
            "precio_unitario",
            "precio_base_paquete",
            "costo_total_estimado",
            "seña_total",
            "monto_pagado",
            "estado",
            "pasajeros",
            "pasajeros_data",
            "activo",
            "fecha_modificacion",
        ]
        read_only_fields = [
            "codigo",
            "fecha_reserva",
            "pasajeros",
            "fecha_modificacion",
            "cantidad_pasajeros",
            "hotel",
            "precio_base_paquete",
            "costo_total_estimado",
            "seña_total"
        ]

    def create(self, validated_data):
        # Extraer pasajeros_data si existe
        pasajeros_data = validated_data.pop("pasajeros_data", [])

        estado_manual = validated_data.get("estado", None)
        instance = super().create(validated_data)

        # Calcular precio_unitario automáticamente si no se proporcionó
        if not instance.precio_unitario and instance.salida and instance.habitacion:
            instance.precio_unitario = instance.calcular_precio_unitario()
            instance.save(update_fields=["precio_unitario"])

        # Si se especificó titular_id, agregarlo automáticamente como pasajero
        if instance.titular:
            Pasajero.objects.create(
                reserva=instance,
                persona_id=instance.titular_id,
                es_titular=True
            )

        # Crear pasajeros asociados (vincular personas existentes a la reserva)
        for pasajero_data in pasajeros_data:
            persona_id = pasajero_data.get("persona_id")

            # Evitar duplicar el titular si ya fue agregado arriba
            if instance.titular and persona_id == instance.titular_id:
                continue

            Pasajero.objects.create(
                reserva=instance,
                persona_id=persona_id,
                es_titular=False
            )

        if not estado_manual:  # si no se pasó manualmente
            instance.actualizar_estado()

        return instance

    def update(self, instance, validated_data):
        # Extraer pasajeros_data si existe (para updates, no se actualizan pasajeros aquí)
        validated_data.pop("pasajeros_data", None)

        estado_manual = validated_data.get("estado", None)
        instance = super().update(instance, validated_data)
        if not estado_manual:  # si no se pasó manualmente
            instance.actualizar_estado()
        return instance


class ServicioSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple para mostrar información básica de un servicio"""
    class Meta:
        model = Servicio
        fields = ["id", "nombre", "descripcion"]


class ReservaServiciosAdicionalesSerializer(serializers.ModelSerializer):
    """Serializer para servicios adicionales de una reserva"""
    servicio = ServicioSimpleSerializer(read_only=True)
    servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(),
        write_only=True,
        source="servicio"
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = ReservaServiciosAdicionales
        fields = [
            "id",
            "reserva",
            "servicio",
            "servicio_id",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "fecha_agregado",
            "observacion",
            "activo",
        ]
        read_only_fields = ["fecha_agregado", "subtotal"]

    def validate_cantidad(self, value):
        """Validar que la cantidad sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_precio_unitario(self, value):
        """Validar que el precio unitario sea mayor o igual a 0"""
        if value < 0:
            raise serializers.ValidationError("El precio unitario no puede ser negativo")
        return value


class ReservaServiciosAdicionalesCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear servicios adicionales sin especificar la reserva en el body"""
    servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(),
        source="servicio"
    )

    class Meta:
        model = ReservaServiciosAdicionales
        fields = [
            "servicio_id",
            "cantidad",
            "precio_unitario",
            "observacion",
        ]

    def validate_cantidad(self, value):
        """Validar que la cantidad sea mayor a 0"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value

    def validate_precio_unitario(self, value):
        """Validar que el precio unitario sea mayor o igual a 0"""
        if value < 0:
            raise serializers.ValidationError("El precio unitario no puede ser negativo")
        return value
