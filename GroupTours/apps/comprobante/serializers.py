from rest_framework import serializers
from .models import ComprobantePago, ComprobantePagoDistribucion, Voucher
from apps.reserva.models import Pasajero
from apps.empleado.models import Empleado
from decimal import Decimal


class ComprobantePagoDistribucionSerializer(serializers.ModelSerializer):
    """
    Serializer para la distribución de pagos entre pasajeros.
    """
    pasajero_nombre = serializers.CharField(source='pasajero.persona.nombre', read_only=True)
    pasajero_apellido = serializers.CharField(source='pasajero.persona.apellido', read_only=True)
    pasajero_documento = serializers.CharField(source='pasajero.persona.numero_documento', read_only=True)

    class Meta:
        model = ComprobantePagoDistribucion
        fields = [
            'id',
            'pasajero',
            'pasajero_nombre',
            'pasajero_apellido',
            'pasajero_documento',
            'monto',
            'observaciones',
            'fecha_creacion',
        ]
        read_only_fields = ['fecha_creacion']

    def validate(self, data):
        """
        Validar que la distribución sea válida.
        """
        # Si estamos actualizando, usar la instancia existente
        if self.instance:
            comprobante = self.instance.comprobante
            pasajero = data.get('pasajero', self.instance.pasajero)
        else:
            # En creación, el comprobante se pasará desde el ComprobantePagoSerializer
            comprobante = self.context.get('comprobante')
            pasajero = data.get('pasajero')

        if not comprobante:
            raise serializers.ValidationError("No se ha especificado el comprobante")

        if not pasajero:
            raise serializers.ValidationError("Debe especificar el pasajero")

        # Validar que el pasajero pertenece a la reserva del comprobante
        if pasajero.reserva != comprobante.reserva:
            raise serializers.ValidationError(
                f"El pasajero no pertenece a la reserva {comprobante.reserva.codigo}"
            )

        # Validar que el monto no exceda el disponible del comprobante
        monto = data.get('monto', Decimal('0'))

        # Calcular monto ya distribuido (excluyendo esta distribución si es actualización)
        otras_distribuciones = comprobante.distribuciones.all()
        if self.instance:
            otras_distribuciones = otras_distribuciones.exclude(id=self.instance.id)

        monto_distribuido = sum(d.monto for d in otras_distribuciones)
        monto_disponible = comprobante.monto - monto_distribuido

        if monto > monto_disponible:
            raise serializers.ValidationError(
                f"El monto excede el disponible. Disponible: ${monto_disponible}"
            )

        return data


class ComprobantePagoSerializer(serializers.ModelSerializer):
    """
    Serializer para comprobantes de pago.
    Permite crear comprobantes con sus distribuciones en una sola operación.
    """
    distribuciones = ComprobantePagoDistribucionSerializer(many=True, required=True)

    # Campos de solo lectura para mostrar información relacionada
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)
    empleado_nombre = serializers.CharField(source='empleado.persona.nombre', read_only=True)
    empleado_apellido = serializers.CharField(source='empleado.persona.apellido', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)

    class Meta:
        model = ComprobantePago
        fields = [
            'id',
            'numero_comprobante',
            'reserva',
            'reserva_codigo',
            'fecha_pago',
            'tipo',
            'tipo_display',
            'monto',
            'metodo_pago',
            'metodo_pago_display',
            'referencia',
            'observaciones',
            'empleado',
            'empleado_nombre',
            'empleado_apellido',
            'pdf_generado',
            'activo',
            'distribuciones',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'numero_comprobante',
            'fecha_pago',
            'fecha_creacion',
            'fecha_modificacion',
        ]

    def validate_distribuciones(self, value):
        """
        Validar que se proporcione al menos una distribución.
        """
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Debe especificar al menos una distribución de pago"
            )
        return value

    def validate(self, data):
        """
        Validar que la suma de distribuciones coincida con el monto total.
        """
        monto_total = data.get('monto', Decimal('0'))
        distribuciones = data.get('distribuciones', [])

        # Calcular suma de distribuciones
        suma_distribuciones = sum(
            Decimal(str(d.get('monto', 0))) for d in distribuciones
        )

        if suma_distribuciones != monto_total:
            raise serializers.ValidationError(
                f"La suma de distribuciones (${suma_distribuciones}) no coincide "
                f"con el monto total (${monto_total})"
            )

        return data

    def create(self, validated_data):
        """
        Crear comprobante con sus distribuciones.
        """
        distribuciones_data = validated_data.pop('distribuciones')

        # Crear el comprobante
        comprobante = ComprobantePago.objects.create(**validated_data)

        # Crear las distribuciones
        for dist_data in distribuciones_data:
            ComprobantePagoDistribucion.objects.create(
                comprobante=comprobante,
                **dist_data
            )

        # Validar que las distribuciones suman el monto total
        comprobante.validar_distribuciones()

        # Actualizar el monto pagado en la reserva
        comprobante.actualizar_monto_reserva()

        return comprobante

    def update(self, instance, validated_data):
        """
        Actualizar comprobante.
        No se permite modificar distribuciones después de crear.
        """
        # Remover distribuciones si se intentan actualizar
        validated_data.pop('distribuciones', None)

        # Actualizar campos permitidos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # Recalcular monto de reserva
        instance.actualizar_monto_reserva()

        return instance


class ComprobantePagoResumenSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar comprobantes.
    """
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    cantidad_distribuciones = serializers.SerializerMethodField()

    class Meta:
        model = ComprobantePago
        fields = [
            'id',
            'numero_comprobante',
            'reserva_codigo',
            'fecha_pago',
            'tipo',
            'tipo_display',
            'monto',
            'metodo_pago',
            'metodo_pago_display',
            'activo',
            'cantidad_distribuciones',
        ]

    def get_cantidad_distribuciones(self, obj):
        return obj.distribuciones.count()


class VoucherSerializer(serializers.ModelSerializer):
    """
    Serializer para vouchers de reserva.
    """
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)
    reserva_estado = serializers.CharField(source='reserva.estado', read_only=True)
    titular_nombre = serializers.CharField(source='reserva.titular.nombre', read_only=True)
    titular_apellido = serializers.CharField(source='reserva.titular.apellido', read_only=True)
    paquete_nombre = serializers.CharField(source='reserva.paquete.nombre', read_only=True)

    # Información de salida
    fecha_salida = serializers.DateField(source='reserva.salida.fecha_salida', read_only=True)
    fecha_regreso = serializers.DateField(source='reserva.salida.fecha_regreso', read_only=True)

    # Información de hotel y habitación
    hotel_nombre = serializers.SerializerMethodField()
    habitacion_numero = serializers.CharField(source='reserva.habitacion.numero', read_only=True)
    habitacion_tipo = serializers.CharField(source='reserva.habitacion.get_tipo_display', read_only=True)

    class Meta:
        model = Voucher
        fields = [
            'id',
            'codigo_voucher',
            'reserva',
            'reserva_codigo',
            'reserva_estado',
            'titular_nombre',
            'titular_apellido',
            'paquete_nombre',
            'fecha_salida',
            'fecha_regreso',
            'hotel_nombre',
            'habitacion_numero',
            'habitacion_tipo',
            'fecha_emision',
            'qr_code',
            'pdf_generado',
            'instrucciones_especiales',
            'contacto_emergencia',
            'url_publica',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'codigo_voucher',
            'fecha_emision',
            'fecha_creacion',
            'fecha_modificacion',
        ]

    def get_hotel_nombre(self, obj):
        if obj.reserva.habitacion and obj.reserva.habitacion.hotel:
            return obj.reserva.habitacion.hotel.nombre
        return None


class VoucherResumenSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar vouchers.
    """
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)
    titular = serializers.SerializerMethodField()

    class Meta:
        model = Voucher
        fields = [
            'id',
            'codigo_voucher',
            'reserva_codigo',
            'titular',
            'fecha_emision',
            'activo',
        ]

    def get_titular(self, obj):
        if obj.reserva.titular:
            return f"{obj.reserva.titular.nombre} {obj.reserva.titular.apellido}"
        return None
