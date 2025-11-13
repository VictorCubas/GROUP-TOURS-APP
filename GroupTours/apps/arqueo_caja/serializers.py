# apps/arqueo_caja/serializers.py
from rest_framework import serializers
from .models import Caja, AperturaCaja, MovimientoCaja, CierreCaja
from apps.facturacion.serializers import PuntoExpedicionSerializer
from apps.empleado.serializers import EmpleadoSerializer


# ================== CAJA ==================

class CajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar cajas (vista resumida)"""
    punto_expedicion_nombre = serializers.CharField(
        source='punto_expedicion.nombre',
        read_only=True
    )

    # Saldo convertido a moneda alternativa (USD si está en PYG, o PYG si está en USD)
    saldo_actual_alternativo = serializers.SerializerMethodField()
    moneda_alternativa = serializers.SerializerMethodField()

    class Meta:
        model = Caja
        fields = [
            'id', 'nombre', 'numero_caja', 'punto_expedicion',
            'punto_expedicion_nombre', 'emite_facturas', 'descripcion', 'ubicacion',
            'estado_actual', 'saldo_actual', 'saldo_actual_alternativo',
            'moneda_alternativa', 'activo'
        ]

    def get_moneda_alternativa(self, obj):
        """
        Retorna la moneda alternativa (USD si está en PYG, o PYG si está en USD).
        Por defecto, asumimos que las cajas operan en PYG, así que la alternativa es USD.
        """
        return 'USD'

    def get_saldo_actual_alternativo(self, obj):
        """
        Convierte el saldo_actual de PYG a USD usando la cotización vigente.
        Asumimos que todas las cajas operan en Guaraníes (PYG).
        """
        from decimal import Decimal
        from apps.moneda.models import Moneda, CotizacionMoneda

        try:
            # Obtener la moneda USD
            moneda_usd = Moneda.objects.get(codigo='USD', activo=True)

            # Obtener cotización vigente
            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)

            if cotizacion:
                # Convertir de PYG a USD (dividir por la cotización)
                saldo_pyg = Decimal(str(obj.saldo_actual))
                valor_cotizacion = Decimal(str(cotizacion.valor_en_guaranies))

                if valor_cotizacion != 0:
                    saldo_usd = saldo_pyg / valor_cotizacion
                    return round(saldo_usd, 2)
                else:
                    return 0.00
            else:
                # No hay cotización disponible
                return None

        except Moneda.DoesNotExist:
            # Moneda USD no existe en el sistema
            return None
        except Exception:
            return None


class CajaDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de caja (vista completa)"""
    punto_expedicion = PuntoExpedicionSerializer(read_only=True)

    class Meta:
        model = Caja
        fields = '__all__'


class CajaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar cajas"""

    class Meta:
        model = Caja
        fields = [
            'nombre', 'punto_expedicion',
            'emite_facturas', 'descripcion', 'ubicacion', 'activo'
        ]
        # numero_caja se genera automáticamente

    def validate(self, data):
        # Para actualización (PATCH/PUT), usar la instancia existente
        if self.instance:
            # Crear una copia de los valores actuales
            temp_data = {
                'nombre': self.instance.nombre,
                'punto_expedicion': self.instance.punto_expedicion,
                'emite_facturas': self.instance.emite_facturas,
                'descripcion': self.instance.descripcion,
                'ubicacion': self.instance.ubicacion,
                'activo': self.instance.activo,
            }
            # Actualizar con los nuevos valores del payload
            temp_data.update(data)

            # Crear instancia temporal con todos los datos
            temp_instance = Caja(**temp_data)
            temp_instance.pk = self.instance.pk  # Mantener el ID
            temp_instance.clean()
        else:
            # Para creación, crear instancia temporal
            instance = Caja(**data)
            instance.clean()

        return data


# ================== APERTURA CAJA ==================

class AperturaCajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar aperturas (vista resumida)"""
    caja_nombre = serializers.CharField(source='caja.nombre', read_only=True)
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = AperturaCaja
        fields = [
            'id', 'codigo_apertura', 'caja', 'caja_nombre',
            'responsable', 'responsable_nombre', 'fecha_hora_apertura',
            'monto_inicial', 'esta_abierta', 'activo'
        ]

    def get_responsable_nombre(self, obj):
        if obj.responsable and obj.responsable.persona:
            return f"{obj.responsable.persona.nombre} {obj.responsable.persona.apellido}"
        return None


class AperturaCajaDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de apertura (vista completa)"""
    caja = CajaListSerializer(read_only=True)
    responsable = EmpleadoSerializer(read_only=True)
    movimientos_count = serializers.SerializerMethodField()

    class Meta:
        model = AperturaCaja
        fields = '__all__'
        extra_fields = ['movimientos_count']

    def get_fields(self):
        fields = super().get_fields()
        # Agregar campos extras
        for field in self.Meta.extra_fields:
            if field not in fields:
                pass  # Ya está definido como SerializerMethodField
        return fields

    def get_movimientos_count(self, obj):
        return obj.movimientos.filter(activo=True).count()


class AperturaCajaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear aperturas"""

    class Meta:
        model = AperturaCaja
        fields = [
            'caja', 'responsable', 'monto_inicial', 'observaciones_apertura'
        ]

    def validate(self, data):
        # Llamar al método clean del modelo para validaciones de negocio
        instance = AperturaCaja(**data)
        instance.clean()
        return data


# ================== MOVIMIENTO CAJA ==================

class MovimientoCajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar movimientos (vista resumida)"""
    tipo_movimiento_display = serializers.CharField(
        source='get_tipo_movimiento_display',
        read_only=True
    )
    concepto_display = serializers.SerializerMethodField()
    metodo_pago_display = serializers.CharField(
        source='get_metodo_pago_display',
        read_only=True
    )
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoCaja
        fields = [
            'id', 'numero_movimiento', 'apertura_caja', 'comprobante',
            'tipo_movimiento', 'tipo_movimiento_display', 'concepto',
            'concepto_display', 'monto', 'metodo_pago', 'metodo_pago_display',
            'referencia', 'fecha_hora_movimiento', 'usuario_registro',
            'usuario_nombre', 'activo'
        ]

    def get_concepto_display(self, obj):
        # Buscar el display name en las choices
        if obj.tipo_movimiento == 'ingreso':
            for value, display in MovimientoCaja.CONCEPTOS_INGRESO:
                if value == obj.concepto:
                    return display
        elif obj.tipo_movimiento == 'egreso':
            for value, display in MovimientoCaja.CONCEPTOS_EGRESO:
                if value == obj.concepto:
                    return display
        return obj.concepto

    def get_usuario_nombre(self, obj):
        if obj.usuario_registro and obj.usuario_registro.persona:
            return f"{obj.usuario_registro.persona.nombre} {obj.usuario_registro.persona.apellido}"
        return None


class MovimientoCajaDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de movimiento (vista completa)"""
    apertura_caja = AperturaCajaListSerializer(read_only=True)
    usuario_registro = EmpleadoSerializer(read_only=True)
    tipo_movimiento_display = serializers.CharField(
        source='get_tipo_movimiento_display',
        read_only=True
    )
    metodo_pago_display = serializers.CharField(
        source='get_metodo_pago_display',
        read_only=True
    )

    class Meta:
        model = MovimientoCaja
        fields = '__all__'


class MovimientoCajaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear movimientos"""

    class Meta:
        model = MovimientoCaja
        fields = [
            'apertura_caja', 'comprobante', 'tipo_movimiento', 'concepto',
            'monto', 'metodo_pago', 'referencia', 'descripcion', 'usuario_registro'
        ]

    def validate(self, data):
        # Llamar al método clean del modelo para validaciones de negocio
        instance = MovimientoCaja(**data)
        instance.clean()
        return data


# ================== CIERRE CAJA ==================

class CierreCajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar cierres (vista resumida)"""
    caja_nombre = serializers.CharField(
        source='apertura_caja.caja.nombre',
        read_only=True
    )
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = CierreCaja
        fields = [
            'id', 'codigo_cierre', 'apertura_caja', 'caja_nombre',
            'responsable_nombre', 'fecha_hora_cierre', 'saldo_teorico_efectivo',
            'saldo_real_efectivo', 'diferencia_efectivo', 'diferencia_porcentaje',
            'requiere_autorizacion', 'activo'
        ]

    def get_responsable_nombre(self, obj):
        if obj.apertura_caja.responsable and obj.apertura_caja.responsable.persona:
            persona = obj.apertura_caja.responsable.persona
            return f"{persona.nombre} {persona.apellido}"
        return None


class CierreCajaDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de cierre (vista completa con resumen)"""
    apertura_caja = AperturaCajaDetailSerializer(read_only=True)
    autorizado_por = EmpleadoSerializer(read_only=True)
    resumen = serializers.SerializerMethodField()

    class Meta:
        model = CierreCaja
        fields = '__all__'
        extra_fields = ['resumen']

    def get_fields(self):
        fields = super().get_fields()
        return fields

    def get_resumen(self, obj):
        return obj.generar_resumen()


class CierreCajaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear cierres"""

    class Meta:
        model = CierreCaja
        fields = [
            'apertura_caja', 'saldo_real_efectivo', 'detalle_billetes',
            'observaciones_cierre', 'justificacion_diferencia'
        ]

    def validate(self, data):
        # Validar que la apertura esté abierta
        apertura = data.get('apertura_caja')
        if not apertura.esta_abierta:
            raise serializers.ValidationError(
                "No se puede cerrar una caja que ya está cerrada"
            )
        return data

    def create(self, validated_data):
        # Crear el cierre
        cierre = CierreCaja.objects.create(**validated_data)

        # Calcular totales automáticamente
        cierre.calcular_totales_desde_movimientos()

        return cierre


class CierreCajaAutorizarSerializer(serializers.Serializer):
    """Serializer para autorizar un cierre con diferencia"""
    autorizado_por = serializers.IntegerField(
        help_text="ID del empleado supervisor que autoriza"
    )
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Observaciones adicionales de la autorización"
    )

    def validate_autorizado_por(self, value):
        from apps.empleado.models import Empleado
        try:
            empleado = Empleado.objects.get(pk=value, activo=True)
            return empleado
        except Empleado.DoesNotExist:
            raise serializers.ValidationError("Empleado no encontrado o inactivo")
