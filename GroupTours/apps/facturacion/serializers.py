# apps/facturacion/serializers.py
from rest_framework import serializers
from .models import (
    Empresa, Establecimiento, PuntoExpedicion,
    TipoImpuesto, SubtipoImpuesto, Timbrado, FacturaElectronica, DetalleFactura
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
    reserva_codigo = serializers.CharField(source='reserva.codigo', read_only=True)

    # NUEVO: Campos para facturación dual
    tipo_facturacion_display = serializers.CharField(source='get_tipo_facturacion_display', read_only=True)
    pasajero_nombre = serializers.SerializerMethodField(read_only=True)

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
            'total_general'
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

    class Meta:
        model = FacturaElectronica
        fields = '__all__'
