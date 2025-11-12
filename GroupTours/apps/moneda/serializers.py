from rest_framework import serializers
from .models import Moneda, CotizacionMoneda


class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id', 'nombre', 'simbolo', 'codigo', 'activo', 'fecha_creacion', 'fecha_modificacion']


class CotizacionMonedaSerializer(serializers.ModelSerializer):
    """Serializer para lectura de cotizaciones"""
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True)
    moneda_simbolo = serializers.CharField(source='moneda.simbolo', read_only=True)
    usuario_nombre = serializers.SerializerMethodField(read_only=True)

    def get_usuario_nombre(self, obj):
        """Obtiene el nombre del usuario que registró la cotización"""
        if obj.usuario_registro:
            return f"{obj.usuario_registro.first_name} {obj.usuario_registro.last_name}".strip() or obj.usuario_registro.username
        return None

    class Meta:
        model = CotizacionMoneda
        fields = [
            'id',
            'moneda',
            'moneda_nombre',
            'moneda_codigo',
            'moneda_simbolo',
            'valor_en_guaranies',
            'fecha_vigencia',
            'usuario_registro',
            'usuario_nombre',
            'observaciones',
            'fecha_creacion',
            'fecha_modificacion'
        ]
        read_only_fields = ['usuario_registro', 'fecha_creacion', 'fecha_modificacion']


class CotizacionMonedaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar cotizaciones"""

    class Meta:
        model = CotizacionMoneda
        fields = [
            'moneda',
            'valor_en_guaranies',
            'fecha_vigencia',
            'observaciones'
        ]

    def validate_valor_en_guaranies(self, value):
        """Validar que el valor sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El valor de cotización debe ser mayor a 0")
        return value

    def validate(self, attrs):
        """Validaciones adicionales"""
        from django.utils import timezone

        # Validar que no sea fecha futura
        fecha_vigencia = attrs.get('fecha_vigencia')
        if fecha_vigencia and fecha_vigencia > timezone.now().date():
            raise serializers.ValidationError({
                'fecha_vigencia': 'No se puede registrar cotización para fechas futuras'
            })

        return attrs
