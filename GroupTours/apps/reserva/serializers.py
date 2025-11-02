from rest_framework import serializers
from .models import Reserva, Pasajero, ReservaServiciosAdicionales
from apps.persona.models import PersonaFisica
from apps.paquete.models import SalidaPaquete
from apps.paquete.serializers import PaqueteSerializer
from apps.hotel.models import Hotel, Habitacion
from apps.servicio.models import Servicio


class PersonaFisicaSimpleSerializer(serializers.ModelSerializer):
    nacionalidad_nombre = serializers.CharField(source='nacionalidad.nombre', read_only=True)
    tipo_documento_nombre = serializers.CharField(source='tipo_documento.nombre', read_only=True)
    sexo_display = serializers.CharField(source='get_sexo_display', read_only=True)

    class Meta:
        model = PersonaFisica
        fields = ["id", "nombre", "apellido", "documento", "tipo_documento", "tipo_documento_nombre", "email", "telefono", "fecha_nacimiento", "sexo", "sexo_display", "nacionalidad", "nacionalidad_nombre"]


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
    persona_id = serializers.PrimaryKeyRelatedField(
        queryset=PersonaFisica.objects.all(),
        source='persona',
        write_only=True,
        required=False,
        help_text="ID de la PersonaFisica para asignar/actualizar al pasajero"
    )

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

    # Información del voucher
    voucher_id = serializers.SerializerMethodField(
        help_text="ID del voucher asociado al pasajero (si existe)"
    )

    # Información de facturación individual
    puede_descargar_factura = serializers.SerializerMethodField(
        help_text="Indica si el pasajero puede descargar su factura individual"
    )
    factura_id = serializers.SerializerMethodField(
        help_text="ID de la factura individual del pasajero (si existe)"
    )

    class Meta:
        model = Pasajero
        fields = [
            "id",
            "persona",
            "persona_id",
            "es_titular",
            "por_asignar",
            "precio_asignado",
            "monto_pagado",
            "saldo_pendiente",
            "porcentaje_pagado",
            "seña_requerida",
            "tiene_sena_pagada",
            "esta_totalmente_pagado",
            "ticket_numero",
            "voucher_codigo",
            "voucher_id",
            "fecha_registro",
            "puede_descargar_factura",
            "factura_id",
        ]
        read_only_fields = [
            "monto_pagado",
            "saldo_pendiente",
            "porcentaje_pagado",
            "seña_requerida",
            "tiene_sena_pagada",
            "esta_totalmente_pagado",
        ]

    def get_voucher_id(self, obj):
        """
        Obtiene el ID del voucher asociado al pasajero.
        Retorna None si el pasajero no tiene voucher generado.
        """
        if hasattr(obj, 'voucher') and obj.voucher:
            return obj.voucher.id
        return None

    def get_puede_descargar_factura(self, obj):
        """
        Determina si el pasajero cumple las condiciones para generar/descargar su factura individual.
        Solo aplica si la reserva está en modalidad 'individual'.

        Condiciones para habilitar el botón "Generar y Descargar Factura":
        - Reserva en modalidad 'individual'
        - Reserva en estado 'confirmada' o 'finalizada'
        - Pasajero totalmente pagado (100% del precio asignado)
        - Pasajero no es temporal (por_asignar=False, tiene datos reales)

        NOTA: Este campo indica si se PUEDE generar la factura, no si ya existe.
        El frontend debe mostrar el botón habilitado si este campo es True.
        """
        reserva = obj.reserva

        # Si la modalidad no es individual, no aplica
        if reserva.modalidad_facturacion != 'individual':
            return False

        # La reserva debe estar confirmada o finalizada
        if reserva.estado not in ['confirmada', 'finalizada']:
            return False

        # Si el pasajero no está totalmente pagado, no puede generar factura
        if not obj.esta_totalmente_pagado:
            return False

        # Si el pasajero es temporal (por asignar), no puede generar factura
        if obj.por_asignar:
            return False

        # Si cumple todas las condiciones, puede generar/descargar la factura
        return True

    def get_factura_id(self, obj):
        """
        Obtiene el ID de la factura individual del pasajero.
        Retorna None si no tiene factura o no es modalidad individual.
        """
        reserva = obj.reserva

        # Solo retornar si es modalidad individual
        if reserva.modalidad_facturacion != 'individual':
            return None

        # Buscar factura individual activa
        factura = obj.facturas.filter(
            tipo_facturacion='por_pasajero',
            activo=True
        ).first()

        return factura.id if factura else None


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
    # NUEVO: Campo para mostrar la modalidad de facturación en formato legible
    modalidad_facturacion_display = serializers.CharField(
        source='get_modalidad_facturacion_display',
        read_only=True,
        help_text="Modalidad de facturación en formato legible"
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
            "modalidad_facturacion",  # NUEVO
            "modalidad_facturacion_display",  # NUEVO
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

    # Información del voucher
    voucher_id = serializers.SerializerMethodField(
        help_text="ID del voucher asociado al pasajero (si existe)"
    )

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
            'voucher_id',
            'fecha_registro',
            'historial_pagos',
        ]

    def get_voucher_id(self, obj):
        """
        Obtiene el ID del voucher asociado al pasajero.
        Retorna None si el pasajero no tiene voucher generado.
        """
        if hasattr(obj, 'voucher') and obj.voucher:
            return obj.voucher.id
        return None

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


class ReservaListadoSerializer(serializers.ModelSerializer):
    """
    Serializer optimizado para listar reservas con información mínima necesaria.
    Ideal para listados, tablas y vistas de resumen.
    """
    # Titular
    titular_nombre = serializers.SerializerMethodField()
    titular_documento = serializers.CharField(source='titular.documento', read_only=True)

    # Paquete
    paquete_nombre = serializers.CharField(source='paquete.nombre', read_only=True)
    paquete_imagen = serializers.SerializerMethodField()
    paquete_ciudad = serializers.SerializerMethodField()
    paquete_pais = serializers.SerializerMethodField()

    # Moneda
    moneda = serializers.SerializerMethodField()

    # Campos calculados
    precio_unitario = serializers.DecimalField(
        source='precio_base_paquete',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    costo_total_estimado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    estado_display = serializers.CharField(read_only=True)

    class Meta:
        model = Reserva
        fields = [
            'id',
            'codigo',
            'estado',
            'estado_display',
            'activo',
            'fecha_reserva',
            'cantidad_pasajeros',
            'titular_nombre',
            'titular_documento',
            'paquete_nombre',
            'paquete_imagen',
            'paquete_ciudad',
            'paquete_pais',
            'moneda',
            'precio_unitario',
            'costo_total_estimado',
        ]

    def get_titular_nombre(self, obj):
        """Nombre completo del titular"""
        if not obj.titular:
            return None
        return f"{obj.titular.nombre} {obj.titular.apellido or ''}".strip()

    def get_paquete_imagen(self, obj):
        """URL de la imagen del paquete"""
        if obj.paquete and obj.paquete.imagen:
            return obj.paquete.imagen.url
        return None

    def get_paquete_ciudad(self, obj):
        """Ciudad del destino del paquete"""
        if obj.paquete and obj.paquete.destino:
            if hasattr(obj.paquete.destino, 'ciudad') and obj.paquete.destino.ciudad:
                return obj.paquete.destino.ciudad.nombre
        return None

    def get_paquete_pais(self, obj):
        """País del destino del paquete"""
        if obj.paquete and obj.paquete.destino:
            if hasattr(obj.paquete.destino, 'ciudad') and obj.paquete.destino.ciudad:
                if hasattr(obj.paquete.destino.ciudad, 'pais') and obj.paquete.destino.ciudad.pais:
                    return obj.paquete.destino.ciudad.pais.nombre
        return None

    def get_moneda(self, obj):
        """Información de la moneda"""
        if obj.paquete and obj.paquete.moneda:
            return {
                'id': obj.paquete.moneda.id,
                'nombre': obj.paquete.moneda.nombre,
                'simbolo': obj.paquete.moneda.simbolo,
                'codigo': obj.paquete.moneda.codigo,
            }
        return None


class ReservaDetalleSerializer(serializers.ModelSerializer):
    """
    Serializer completo para mostrar todos los detalles de una reserva.
    Incluye información completa del paquete, salida, hotel, pasajeros, pagos y servicios.
    """
    # Información del titular
    titular = PersonaFisicaSimpleSerializer(read_only=True)

    # Información del paquete (completa)
    paquete = serializers.SerializerMethodField()

    # Información de la salida (completa)
    salida = serializers.SerializerMethodField()

    # Información del hotel y habitación
    hotel = serializers.SerializerMethodField()
    habitacion = serializers.SerializerMethodField()

    # Pasajeros con toda su información de pagos
    pasajeros = PasajeroSerializer(many=True, read_only=True)

    # Servicios adicionales
    servicios_adicionales = ReservaServiciosAdicionalesSerializer(many=True, read_only=True)

    # Servicios base del paquete
    servicios_base = serializers.SerializerMethodField()

    # Comprobantes de pago
    comprobantes = serializers.SerializerMethodField()

    # Campos calculados de costos
    precio_base_paquete = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    costo_servicios_adicionales = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    costo_total_estimado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    seña_total = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    saldo_pendiente = serializers.SerializerMethodField()

    # Estado
    estado_display = serializers.CharField(read_only=True)
    puede_confirmarse = serializers.SerializerMethodField()
    esta_totalmente_pagada = serializers.SerializerMethodField()

    # Modalidad de facturación
    modalidad_facturacion_display = serializers.CharField(
        source='get_modalidad_facturacion_display',
        read_only=True,
        help_text="Modalidad de facturación en formato legible"
    )

    # Información de facturación
    puede_descargar_factura_global = serializers.SerializerMethodField(
        help_text="Indica si se puede generar/descargar la factura global de la reserva"
    )
    factura_global_id = serializers.SerializerMethodField(
        help_text="ID de la factura global (si existe)"
    )

    class Meta:
        model = Reserva
        fields = [
            'id',
            'codigo',
            'fecha_reserva',
            'fecha_modificacion',
            'observacion',
            'activo',
            # Titular
            'titular',
            # Paquete
            'paquete',
            'salida',
            # Hotel y habitación
            'hotel',
            'habitacion',
            # Pasajeros
            'cantidad_pasajeros',
            'pasajeros',
            'datos_completos',
            # Costos
            'precio_unitario',
            'precio_base_paquete',
            'costo_servicios_adicionales',
            'costo_total_estimado',
            'seña_total',
            'monto_pagado',
            'saldo_pendiente',
            # Estado
            'estado',
            'estado_display',
            'puede_confirmarse',
            'esta_totalmente_pagada',
            # Modalidad de facturación
            'modalidad_facturacion',
            'modalidad_facturacion_display',
            'puede_descargar_factura_global',
            'factura_global_id',
            # Servicios
            'servicios_base',
            'servicios_adicionales',
            # Comprobantes
            'comprobantes',
        ]

    def get_paquete(self, obj):
        """Información completa del paquete"""
        if not obj.paquete:
            return None

        paquete = obj.paquete

        # Construir información del destino de forma segura
        destino_data = None
        if paquete.destino:
            destino_data = {
                'id': paquete.destino.id,
                'ciudad': None,
                'pais': None,
            }

            if hasattr(paquete.destino, 'ciudad') and paquete.destino.ciudad:
                destino_data['ciudad'] = paquete.destino.ciudad.nombre

                if hasattr(paquete.destino.ciudad, 'pais') and paquete.destino.ciudad.pais:
                    destino_data['pais'] = paquete.destino.ciudad.pais.nombre

        return {
            'id': paquete.id,
            'nombre': paquete.nombre,
            'tipo_paquete': {
                'id': paquete.tipo_paquete.id,
                'nombre': paquete.tipo_paquete.nombre
            } if paquete.tipo_paquete else None,
            'destino': destino_data,
            'moneda': {
                'id': paquete.moneda.id,
                'nombre': paquete.moneda.nombre,
                'simbolo': paquete.moneda.simbolo,
                'codigo': paquete.moneda.codigo
            } if paquete.moneda else None,
            'modalidad': paquete.modalidad,
            'propio': paquete.propio,
            'personalizado': paquete.personalizado,
            'cantidad_pasajeros': paquete.cantidad_pasajeros,
            'distribuidora': {
                'id': paquete.distribuidora.id,
                'nombre': paquete.distribuidora.nombre
            } if paquete.distribuidora else None,
            'imagen': paquete.imagen.url if paquete.imagen else None,
        }

    def get_salida(self, obj):
        """Información completa de la salida"""
        if not obj.salida:
            return None

        salida = obj.salida
        return {
            'id': salida.id,
            'fecha_salida': salida.fecha_salida,
            'fecha_regreso': salida.fecha_regreso,
            'precio_actual': salida.precio_actual,
            'precio_final': salida.precio_final,
            'precio_venta_sugerido_min': salida.precio_venta_sugerido_min,
            'precio_venta_sugerido_max': salida.precio_venta_sugerido_max,
            'senia': salida.senia,
            'cupo': salida.cupo,
            'ganancia': salida.ganancia,
            'comision': salida.comision,
            'temporada': {
                'id': salida.temporada.id,
                'nombre': salida.temporada.nombre,
                'fecha_inicio': salida.temporada.fecha_inicio,
                'fecha_fin': salida.temporada.fecha_fin,
            } if salida.temporada else None,
            'moneda': {
                'id': salida.moneda.id,
                'nombre': salida.moneda.nombre,
                'simbolo': salida.moneda.simbolo,
                'codigo': salida.moneda.codigo
            } if salida.moneda else None,
        }

    def get_hotel(self, obj):
        """Información completa del hotel"""
        if not obj.habitacion or not obj.habitacion.hotel:
            return None

        hotel = obj.habitacion.hotel
        return {
            'id': hotel.id,
            'nombre': hotel.nombre,
            'direccion': hotel.direccion,
            'descripcion': hotel.descripcion,
            'estrellas': hotel.estrellas,
            'cadena': {
                'id': hotel.cadena.id,
                'nombre': hotel.cadena.nombre
            } if hotel.cadena else None,
            'ciudad': {
                'id': hotel.ciudad.id,
                'nombre': hotel.ciudad.nombre
            } if hotel.ciudad else None,
        }

    def get_habitacion(self, obj):
        """Información completa de la habitación"""
        if not obj.habitacion:
            return None

        habitacion = obj.habitacion
        return {
            'id': habitacion.id,
            'numero': habitacion.numero,
            'tipo': habitacion.tipo,
            'tipo_display': habitacion.get_tipo_display(),
            'capacidad': habitacion.capacidad,
            'precio_noche': habitacion.precio_noche,
            'moneda': {
                'id': habitacion.moneda.id,
                'nombre': habitacion.moneda.nombre,
                'simbolo': habitacion.moneda.simbolo,
                'codigo': habitacion.moneda.codigo
            } if habitacion.moneda else None,
        }

    def get_servicios_base(self, obj):
        """Servicios incluidos en el paquete base"""
        if not obj.paquete:
            return []

        servicios = []
        for ps in obj.paquete.paquete_servicios.all():
            servicios.append({
                'id': ps.id,
                'servicio': {
                    'id': ps.servicio.id,
                    'nombre': ps.servicio.nombre,
                    'descripcion': ps.servicio.descripcion,
                    'tipo': ps.servicio.tipo,
                },
                'precio': ps.precio,
            })
        return servicios

    def get_comprobantes(self, obj):
        """Historial de los últimos 3 comprobantes de pago"""
        comprobantes = obj.comprobantes.filter(activo=True).order_by('-fecha_pago')[:3]

        resultado = []
        for comp in comprobantes:
            # Obtener distribuciones de este comprobante
            distribuciones = []
            for dist in comp.distribuciones.all():
                distribuciones.append({
                    'pasajero_id': dist.pasajero.id,
                    'pasajero_nombre': f"{dist.pasajero.persona.nombre} {dist.pasajero.persona.apellido}",
                    'monto': dist.monto,
                    'observaciones': dist.observaciones,
                })

            # Obtener nombre del empleado de forma segura
            empleado_data = None
            if comp.empleado:
                # El empleado tiene una relación con Persona, pero necesitamos PersonaFisica
                persona = comp.empleado.persona
                if hasattr(persona, 'personafisica'):
                    # Acceder al objeto PersonaFisica a través de la relación polimórfica
                    pf = persona.personafisica
                    empleado_data = {
                        'id': comp.empleado.id,
                        'nombre': f"{pf.nombre} {pf.apellido or ''}".strip(),
                    }
                elif hasattr(persona, 'nombre'):
                    # Si la persona ya es PersonaFisica
                    empleado_data = {
                        'id': comp.empleado.id,
                        'nombre': f"{persona.nombre} {getattr(persona, 'apellido', '') or ''}".strip(),
                    }
                else:
                    # Fallback: usar el documento
                    empleado_data = {
                        'id': comp.empleado.id,
                        'nombre': persona.documento,
                    }

            resultado.append({
                'id': comp.id,
                'numero_comprobante': comp.numero_comprobante,
                'fecha_pago': comp.fecha_pago,
                'fecha_creacion': comp.fecha_creacion,
                'tipo': comp.tipo,
                'tipo_display': comp.get_tipo_display(),
                'metodo_pago': comp.metodo_pago,
                'metodo_pago_display': comp.get_metodo_pago_display(),
                'monto': comp.monto,
                'referencia': comp.referencia,
                'observaciones': comp.observaciones,
                'distribuciones': distribuciones,
                'empleado': empleado_data,
                'pdf_url': comp.pdf_generado.url if comp.pdf_generado else None,
            })

        return resultado

    def get_saldo_pendiente(self, obj):
        """Saldo pendiente de pago"""
        return obj.costo_total_estimado - obj.monto_pagado

    def get_puede_confirmarse(self, obj):
        """Si la reserva puede confirmarse"""
        return obj.puede_confirmarse()

    def get_esta_totalmente_pagada(self, obj):
        """Si la reserva está totalmente pagada"""
        return obj.esta_totalmente_pagada()

    def get_puede_descargar_factura_global(self, obj):
        """
        Determina si se puede generar/descargar la factura global de la reserva.
        Solo aplica si la reserva está en modalidad 'global'.

        Condiciones para habilitar el botón "Generar Factura":
        - Reserva en modalidad 'global'
        - Reserva en estado 'finalizada'
        - Reserva totalmente pagada

        NOTA: No se requiere que la factura ya esté generada. Este campo
        indica si se PUEDE generar la factura (si aún no existe) o descargarla
        (si ya existe).
        """
        # Si la modalidad no es global, no aplica
        if obj.modalidad_facturacion != 'global':
            return False

        # Si la reserva no está finalizada, no puede generar factura
        if obj.estado != 'finalizada':
            return False

        # Si la reserva no está totalmente pagada, no puede generar factura
        if not obj.esta_totalmente_pagada():
            return False

        # Si cumple todas las condiciones, puede generar/descargar la factura
        return True

    def get_factura_global_id(self, obj):
        """
        Obtiene el ID de la factura global de la reserva.
        Retorna None si no tiene factura global o no es modalidad global.
        """
        # Solo retornar si es modalidad global
        if obj.modalidad_facturacion != 'global':
            return None

        # Buscar factura global activa
        factura = obj.facturas.filter(
            tipo_facturacion='total',
            activo=True
        ).first()

        return factura.id if factura else None
