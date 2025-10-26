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

    # Campos calculados de pagos
    monto_pagado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Monto total pagado por este pasajero"
    )
    saldo_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Saldo que le falta pagar a este pasajero"
    )
    porcentaje_pagado = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True,
        help_text="Porcentaje del precio pagado (0-100)"
    )
    seña_requerida = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
        help_text="Monto de seña requerido para este pasajero"
    )
    tiene_sena_pagada = serializers.BooleanField(
        read_only=True,
        help_text="Indica si tiene su seña completa pagada"
    )
    esta_totalmente_pagado = serializers.BooleanField(
        read_only=True,
        help_text="Indica si tiene el 100% pagado"
    )

    class Meta:
        model = Pasajero
        fields = [
            "id",
            "persona",
            "es_titular",
            "precio_asignado",
            "monto_pagado",
            "saldo_pendiente",
            "porcentaje_pagado",
            "seña_requerida",
            "tiene_sena_pagada",
            "esta_totalmente_pagado",
            "ticket_numero",
            "voucher_codigo",
            "fecha_registro",
        ]
        read_only_fields = [
            "monto_pagado",
            "saldo_pendiente",
            "porcentaje_pagado",
            "seña_requerida",
            "tiene_sena_pagada",
            "esta_totalmente_pagado",
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
        required=True,
        help_text="ID del titular de la reserva (obligatorio)"
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

    # Bandera para controlar si el titular se agrega automáticamente como pasajero
    titular_como_pasajero = serializers.BooleanField(
        write_only=True,
        required=False,
        default=True,
        help_text="Si es True, el titular se agrega automáticamente como pasajero. Default: True"
    )

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
    estado_display = serializers.CharField(
        read_only=True,
        help_text="Texto descriptivo del estado para mostrar en UI"
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
            "datos_completos",
            "estado_display",
            "pasajeros",
            "pasajeros_data",
            "titular_como_pasajero",
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
            "seña_total",
            "datos_completos",
            "estado_display"
        ]

    def create(self, validated_data):
        # Validar que el titular esté presente
        if 'titular' not in validated_data or validated_data['titular'] is None:
            raise serializers.ValidationError({
                'titular_id': 'El titular es obligatorio al crear una reserva.'
            })

        # Extraer pasajeros_data si existe
        pasajeros_data = validated_data.pop("pasajeros_data", [])

        # Extraer la bandera titular_como_pasajero (default: True para mantener compatibilidad)
        titular_como_pasajero = validated_data.pop("titular_como_pasajero", True)

        estado_manual = validated_data.get("estado", None)
        instance = super().create(validated_data)

        # Calcular precio_unitario automáticamente si no se proporcionó
        if not instance.precio_unitario and instance.salida and instance.habitacion:
            instance.precio_unitario = instance.calcular_precio_unitario()
            instance.save(update_fields=["precio_unitario"])

        # Si se especificó titular_id Y la bandera titular_como_pasajero es True, agregarlo como pasajero
        if instance.titular and titular_como_pasajero:
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


class PagoHistorialSerializer(serializers.Serializer):
    """
    Serializer para el historial de pagos de un pasajero.
    NO es un ModelSerializer porque representa datos de múltiples modelos.
    """
    fecha_pago = serializers.DateTimeField(help_text="Fecha del pago")
    numero_comprobante = serializers.CharField(help_text="Número del comprobante")
    tipo = serializers.CharField(help_text="Tipo de pago")
    tipo_display = serializers.CharField(help_text="Tipo de pago legible")
    metodo_pago = serializers.CharField(help_text="Método de pago")
    metodo_pago_display = serializers.CharField(help_text="Método de pago legible")
    monto_distribuido = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto asignado a este pasajero"
    )
    comprobante_activo = serializers.BooleanField(help_text="Si el comprobante está activo")
    observaciones = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        help_text="Observaciones de la distribución"
    )


class PasajeroEstadoCuentaSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el estado de cuenta de un pasajero.
    Incluye toda la información financiera y el historial de pagos.
    """
    persona = PersonaFisicaSimpleSerializer(read_only=True)
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)
    paquete_nombre = serializers.CharField(source='reserva.paquete.nombre', read_only=True)

    # Campos calculados de pagos (heredados del modelo)
    monto_pagado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    saldo_pendiente = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    porcentaje_pagado = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        read_only=True
    )
    seña_requerida = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    tiene_sena_pagada = serializers.BooleanField(read_only=True)
    esta_totalmente_pagado = serializers.BooleanField(read_only=True)

    # Historial de pagos
    historial_pagos = serializers.SerializerMethodField()

    class Meta:
        model = Pasajero
        fields = [
            'id',
            'reserva_codigo',
            'paquete_nombre',
            'persona',
            'es_titular',
            'precio_asignado',
            'monto_pagado',
            'saldo_pendiente',
            'porcentaje_pagado',
            'seña_requerida',
            'tiene_sena_pagada',
            'esta_totalmente_pagado',
            'ticket_numero',
            'voucher_codigo',
            'fecha_registro',
            'historial_pagos',
        ]

    def get_historial_pagos(self, obj):
        """
        Obtiene el historial de pagos (distribuciones) de este pasajero.
        """
        distribuciones = obj.distribuciones_pago.select_related(
            'comprobante'
        ).order_by('-comprobante__fecha_pago')

        historial = []
        for dist in distribuciones:
            historial.append({
                'fecha_pago': dist.comprobante.fecha_pago,
                'numero_comprobante': dist.comprobante.numero_comprobante,
                'tipo': dist.comprobante.tipo,
                'tipo_display': dist.comprobante.get_tipo_display(),
                'metodo_pago': dist.comprobante.metodo_pago,
                'metodo_pago_display': dist.comprobante.get_metodo_pago_display(),
                'monto_distribuido': dist.monto,
                'comprobante_activo': dist.comprobante.activo,
                'observaciones': dist.observaciones,
            })

        return historial
