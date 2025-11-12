# apps/facturacion/serializers.py
from rest_framework import serializers
from .models import (
    Empresa, Establecimiento, PuntoExpedicion,
    TipoImpuesto, SubtipoImpuesto, Timbrado, FacturaElectronica, DetalleFactura,
    NotaCreditoElectronica, DetalleNotaCredito
)

class EstablecimientoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establecimiento
        fields = ['id', 'nombre']

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = '__all__'

class EstablecimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establecimiento
        fields = '__all__'

class PuntoExpedicionSerializer(serializers.ModelSerializer):
    establecimiento = EstablecimientoSimpleSerializer(read_only=True)
    class Meta:
        model = PuntoExpedicion
        fields = '__all__'

class SubtipoImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubtipoImpuesto
        fields = '__all__'

class TipoImpuestoSerializer(serializers.ModelSerializer):
    subtipos = SubtipoImpuestoSerializer(many=True, read_only=True)
    class Meta:
        model = TipoImpuesto
        fields = ['id', 'nombre', 'descripcion', 'subtipos']

class TimbradoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Timbrado
        fields = '__all__'

class DetalleFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleFactura
        fields = '__all__'
        read_only_fields = ('subtotal',)


class FacturaElectronicaSerializer(serializers.ModelSerializer):
    detalles = DetalleFacturaSerializer(many=True, read_only=True)

    # Campos relacionados para lectura
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    establecimiento_nombre = serializers.CharField(source='establecimiento.nombre', read_only=True)
    punto_expedicion_nombre = serializers.CharField(source='punto_expedicion.nombre', read_only=True)
    timbrado_numero = serializers.CharField(source='timbrado.numero', read_only=True)
    tipo_impuesto_nombre = serializers.CharField(source='tipo_impuesto.nombre', read_only=True)
    subtipo_impuesto_nombre = serializers.CharField(source='subtipo_impuesto.nombre', read_only=True)
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)

    # NUEVO: Campos de conversión de moneda
    moneda_original_nombre = serializers.CharField(source='moneda_original.nombre', read_only=True, allow_null=True)
    moneda_original_codigo = serializers.CharField(source='moneda_original.codigo', read_only=True, allow_null=True)
    moneda_original_simbolo = serializers.CharField(source='moneda_original.simbolo', read_only=True, allow_null=True)

    # NUEVO: Campos para facturación dual
    tipo_facturacion_display = serializers.CharField(source='get_tipo_facturacion_display', read_only=True)
    pasajero_nombre = serializers.SerializerMethodField(read_only=True)

    # NUEVO: Campos calculados para Notas de Crédito
    total_acreditado = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    saldo_neto = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    esta_totalmente_acreditada = serializers.BooleanField(read_only=True)
    esta_parcialmente_acreditada = serializers.BooleanField(read_only=True)

    def get_pasajero_nombre(self, obj):
        """Obtiene el nombre del pasajero si es factura individual"""
        if obj.pasajero:
            persona = obj.pasajero.persona
            return f"{persona.nombre} {persona.apellido}"
        return None

    class Meta:
        model = FacturaElectronica
        fields = '__all__'
        read_only_fields = (
            'numero_factura',
            'total_exenta',
            'total_gravada_5',
            'total_gravada_10',
            'total_iva_5',
            'total_iva_10',
            'total_iva',
            'total_general',
            'total_acreditado',
            'saldo_neto',
            'esta_totalmente_acreditada',
            'esta_parcialmente_acreditada'
        )


class FacturaElectronicaDetalladaSerializer(serializers.ModelSerializer):
    """
    Serializer con información completa de la factura, incluyendo todos los detalles expandidos
    """
    detalles = DetalleFacturaSerializer(many=True, read_only=True)
    empresa = EmpresaSerializer(read_only=True)
    establecimiento = EstablecimientoSerializer(read_only=True)
    punto_expedicion = PuntoExpedicionSerializer(read_only=True)
    timbrado = TimbradoSerializer(read_only=True)
    tipo_impuesto = TipoImpuestoSerializer(read_only=True)
    subtipo_impuesto = SubtipoImpuestoSerializer(read_only=True)

    # Campos calculados para Notas de Crédito
    total_acreditado = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    saldo_neto = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    esta_totalmente_acreditada = serializers.BooleanField(read_only=True)
    esta_parcialmente_acreditada = serializers.BooleanField(read_only=True)

    class Meta:
        model = FacturaElectronica
        fields = '__all__'


# ========================================
# SERIALIZERS PARA NOTAS DE CRÉDITO
# ========================================

class DetalleNotaCreditoSerializer(serializers.ModelSerializer):
    """Serializer para detalles de nota de crédito"""

    class Meta:
        model = DetalleNotaCredito
        fields = '__all__'
        read_only_fields = ('subtotal',)


class NotaCreditoElectronicaSerializer(serializers.ModelSerializer):
    """Serializer básico para Nota de Crédito"""
    detalles = DetalleNotaCreditoSerializer(many=True, read_only=True)

    # Campos relacionados para lectura
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)
    establecimiento_nombre = serializers.CharField(source='establecimiento.nombre', read_only=True)
    punto_expedicion_nombre = serializers.CharField(source='punto_expedicion.nombre', read_only=True)
    timbrado_numero = serializers.CharField(source='timbrado.numero', read_only=True)
    tipo_impuesto_nombre = serializers.CharField(source='tipo_impuesto.nombre', read_only=True)
    subtipo_impuesto_nombre = serializers.CharField(source='subtipo_impuesto.nombre', read_only=True)
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)

    # Factura afectada
    factura_numero = serializers.CharField(source='factura_afectada.numero_factura', read_only=True)

    # Displays para choices
    tipo_nota_display = serializers.CharField(source='get_tipo_nota_display', read_only=True)
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)

    # Saldo de factura restante
    saldo_factura_restante = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    class Meta:
        model = NotaCreditoElectronica
        fields = '__all__'
        read_only_fields = (
            'numero_nota_credito',
            'total_exenta',
            'total_gravada_5',
            'total_gravada_10',
            'total_iva_5',
            'total_iva_10',
            'total_iva',
            'total_general',
            'saldo_factura_restante'
        )


class NotaCreditoElectronicaDetalladaSerializer(serializers.ModelSerializer):
    """Serializer detallado para Nota de Crédito con toda la información expandida"""
    detalles = DetalleNotaCreditoSerializer(many=True, read_only=True)
    empresa = EmpresaSerializer(read_only=True)
    establecimiento = EstablecimientoSerializer(read_only=True)
    punto_expedicion = PuntoExpedicionSerializer(read_only=True)
    timbrado = TimbradoSerializer(read_only=True)
    tipo_impuesto = TipoImpuestoSerializer(read_only=True)
    subtipo_impuesto = SubtipoImpuestoSerializer(read_only=True)

    # Factura afectada (resumen)
    factura_afectada_detalle = serializers.SerializerMethodField()

    # Displays
    tipo_nota_display = serializers.CharField(source='get_tipo_nota_display', read_only=True)
    motivo_display = serializers.CharField(source='get_motivo_display', read_only=True)

    # Saldo restante
    saldo_factura_restante = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)

    def get_factura_afectada_detalle(self, obj):
        """Retorna resumen de la factura afectada"""
        factura = obj.factura_afectada
        return {
            'id': factura.id,
            'numero_factura': factura.numero_factura,
            'total_general': factura.total_general,
            'total_acreditado': factura.total_acreditado,
            'saldo_neto': factura.saldo_neto,
            'fecha_emision': factura.fecha_emision
        }

    class Meta:
        model = NotaCreditoElectronica
        fields = '__all__'
