# apps/arqueo_caja/serializers.py
from rest_framework import serializers
from .models import Caja, AperturaCaja, MovimientoCaja, CierreCaja
from apps.facturacion.serializers import PuntoExpedicionSerializer
from apps.empleado.serializers import EmpleadoSerializer


# ================== CAJA ==================

class CajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar cajas (vista resumida)"""
    punto_expedicion_codigo = serializers.CharField(
        source='punto_expedicion.codigo',
        read_only=True
    )
    punto_expedicion_nombre = serializers.CharField(
        source='punto_expedicion.nombre',
        read_only=True
    )

    # Información del establecimiento
    establecimiento_codigo = serializers.CharField(
        source='punto_expedicion.establecimiento.codigo',
        read_only=True
    )
    establecimiento_nombre = serializers.CharField(
        source='punto_expedicion.establecimiento.nombre',
        read_only=True
    )

    # Saldo convertido a moneda alternativa (USD si está en PYG, o PYG si está en USD)
    saldo_actual_alternativo = serializers.SerializerMethodField()
    moneda_alternativa = serializers.SerializerMethodField()

    class Meta:
        model = Caja
        fields = [
            'id', 'nombre', 'numero_caja', 'punto_expedicion', 'punto_expedicion_codigo',
            'punto_expedicion_nombre', 'establecimiento_codigo', 'establecimiento_nombre',
            'descripcion', 'estado_actual', 'saldo_actual', 'saldo_actual_alternativo',
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
            'nombre', 'punto_expedicion', 'descripcion', 'activo'
        ]
        # numero_caja se genera automáticamente
        # punto_expedicion es OBLIGATORIO (todas las cajas emiten facturas)

    def validate_punto_expedicion(self, value):
        """Validar que el punto de expedición esté disponible"""
        if value:
            # Para creación o actualización a un PE diferente
            if not self.instance or self.instance.punto_expedicion != value:
                # Verificar que el PE no esté usado por otra caja
                if hasattr(value, 'caja'):
                    raise serializers.ValidationError(
                        f"El punto de expedición '{value}' ya está asignado a la caja '{value.caja.nombre}'"
                    )
        return value

    def validate(self, data):
        # Validar que punto_expedicion sea obligatorio
        if not self.instance and 'punto_expedicion' not in data:
            raise serializers.ValidationError({
                'punto_expedicion': 'Este campo es obligatorio'
            })

        # Para actualización (PATCH/PUT), usar la instancia existente
        if self.instance:
            # Crear una copia de los valores actuales
            temp_data = {
                'nombre': self.instance.nombre,
                'punto_expedicion': self.instance.punto_expedicion,
                'descripcion': self.instance.descripcion,
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
            'monto_inicial', 'observaciones_apertura', 'esta_abierta', 'activo'
        ]

    def get_responsable_nombre(self, obj):
        if obj.responsable and obj.responsable.persona:
            persona = obj.responsable.persona
            try:
                # Intentar acceder a PersonaFisica
                persona_fisica = persona.personafisica
                return f"{persona_fisica.nombre} {persona_fisica.apellido or ''}".strip()
            except:
                pass

            try:
                # Intentar acceder a PersonaJuridica
                persona_juridica = persona.personajuridica
                return persona_juridica.razon_social
            except:
                pass
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
    """Serializer para crear/actualizar aperturas"""

    class Meta:
        model = AperturaCaja
        fields = [
            'caja', 'responsable', 'monto_inicial', 'observaciones_apertura'
        ]
        extra_kwargs = {
            'responsable': {'required': False, 'allow_null': True}
        }

    def validate(self, data):
        # Para actualización (PATCH/PUT), usar la instancia existente
        if self.instance:
            # Crear una copia de los valores actuales
            temp_data = {
                'caja': self.instance.caja,
                'responsable': self.instance.responsable,
                'monto_inicial': self.instance.monto_inicial,
                'observaciones_apertura': self.instance.observaciones_apertura,
            }
            # Actualizar con los nuevos valores del payload
            temp_data.update(data)

            # Crear instancia temporal con todos los datos
            temp_instance = AperturaCaja(**temp_data)
            temp_instance.pk = self.instance.pk  # Mantener el ID para las validaciones
            temp_instance.esta_abierta = self.instance.esta_abierta
            temp_instance.activo = self.instance.activo
            temp_instance.clean()
        else:
            # Para creación, validar solo si se proporciona responsable explícitamente
            # Si no se proporciona, se asignará en la vista
            if 'responsable' in data and data['responsable']:
                instance = AperturaCaja(**data)
                instance.clean()

        return data


# ================== MOVIMIENTO CAJA ==================

class MovimientoCajaListSerializer(serializers.ModelSerializer):
    """Serializer para listar movimientos (vista resumida con información adicional)"""
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
    caja_nombre = serializers.CharField(
        source='apertura_caja.caja.nombre',
        read_only=True
    )
    apertura_codigo = serializers.CharField(
        source='apertura_caja.codigo_apertura',
        read_only=True
    )
    comprobante_numero = serializers.SerializerMethodField()
    tiene_comprobante = serializers.SerializerMethodField()
    
    # Campos de dual-moneda
    monto_gs = serializers.SerializerMethodField()
    monto_usd = serializers.SerializerMethodField()
    moneda_original = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoCaja
        fields = [
            'id', 'numero_movimiento', 'apertura_caja', 'apertura_codigo',
            'caja_nombre', 'comprobante', 'comprobante_numero', 'tiene_comprobante',
            'tipo_movimiento', 'tipo_movimiento_display', 'concepto',
            'concepto_display', 'monto', 'monto_gs', 'monto_usd', 'moneda_original',
            'metodo_pago', 'metodo_pago_display',
            'referencia', 'descripcion', 'fecha_hora_movimiento', 'usuario_registro',
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
            persona = obj.usuario_registro.persona
            try:
                # Intentar acceder a PersonaFisica
                persona_fisica = persona.personafisica
                return f"{persona_fisica.nombre} {persona_fisica.apellido or ''}".strip()
            except:
                pass

            try:
                # Intentar acceder a PersonaJuridica
                persona_juridica = persona.personajuridica
                return persona_juridica.razon_social
            except:
                pass
        return None

    def get_comprobante_numero(self, obj):
        """Retorna el número de comprobante asociado si existe"""
        if obj.comprobante:
            return obj.comprobante.numero_comprobante
        return None

    def get_tiene_comprobante(self, obj):
        """Indica si el movimiento tiene un comprobante asociado"""
        return obj.comprobante is not None
    
    def get_moneda_original(self, obj):
        """
        Detecta la moneda original del paquete asociado al movimiento.
        
        IMPORTANTE: Este campo es SOLO informativo. Indica la moneda del paquete
        de la reserva, NO la moneda en que está guardado el monto.
        
        El campo 'monto' SIEMPRE está en PYG, independientemente de este valor.
        Este campo sirve para saber si el pago original era en USD u otra moneda.
        """
        try:
            if obj.comprobante and obj.comprobante.reserva and obj.comprobante.reserva.paquete:
                moneda_obj = obj.comprobante.reserva.paquete.moneda
                if moneda_obj:
                    return moneda_obj.codigo
        except Exception:
            pass
        
        # Por defecto, asumir PYG
        return "PYG"
    
    def get_monto_gs(self, obj):
        """
        Monto en guaraníes.
        
        IMPORTANTE: Desde la implementación de conversión automática de monedas,
        el campo 'monto' en MovimientoCaja SIEMPRE está en Guaraníes (PYG).
        Los pagos se convierten automáticamente antes de guardarse en caja.
        
        Este campo simplemente retorna el monto tal cual está guardado.
        """
        return float(obj.monto)
    
    def get_monto_usd(self, obj):
        """
        Monto convertido a dólares usando la cotización vigente.
        
        IMPORTANTE: El campo 'monto' en MovimientoCaja SIEMPRE está en Guaraníes (PYG).
        Este método convierte ese monto (PYG) a USD para visualización/referencia.
        
        La conversión es: monto_pyg / cotizacion_usd
        """
        from apps.moneda.models import Moneda, CotizacionMoneda
        from decimal import Decimal
        
        try:
            # El monto siempre está en PYG, convertir a USD para referencia
            moneda_usd = Moneda.objects.get(codigo='USD')
            fecha_movimiento = obj.fecha_hora_movimiento.date()
            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_movimiento)
            
            if cotizacion and cotizacion.valor_en_guaranies > 0:
                # Convertir de PYG a USD
                monto_usd = Decimal(str(obj.monto)) / Decimal(str(cotizacion.valor_en_guaranies))
                return float(round(monto_usd, 2))
            
            return None
            
        except (Moneda.DoesNotExist, Exception):
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
            try:
                # Intentar acceder a PersonaFisica
                persona_fisica = persona.personafisica
                return f"{persona_fisica.nombre} {persona_fisica.apellido or ''}".strip()
            except:
                pass

            try:
                # Intentar acceder a PersonaJuridica
                persona_juridica = persona.personajuridica
                return persona_juridica.razon_social
            except:
                pass
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


class CierreCajaSimpleSerializer(serializers.Serializer):
    """Serializer para cerrar caja de manera simple (endpoint cerrar-simple)"""
    apertura_caja = serializers.IntegerField(
        help_text="ID de la apertura de caja a cerrar"
    )
    saldo_real_efectivo = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Saldo real contado en efectivo"
    )
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Observaciones del cierre"
    )

    def validate_apertura_caja(self, value):
        """Validar que la apertura exista y esté abierta"""
        try:
            apertura = AperturaCaja.objects.get(pk=value, activo=True)
            if not apertura.esta_abierta:
                raise serializers.ValidationError(
                    "No se puede cerrar una caja que ya está cerrada"
                )
            return apertura
        except AperturaCaja.DoesNotExist:
            raise serializers.ValidationError("Apertura no encontrada o inactiva")
