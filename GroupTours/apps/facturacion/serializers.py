# apps/facturacion/serializers.py
from rest_framework import serializers
from .models import (
    Empresa, Establecimiento, PuntoExpedicion,
    TipoImpuesto, SubtipoImpuesto, Timbrado, FacturaElectronica
)


class EstablecimientoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establecimiento
        fields = ['id', 'nombre']  # Solo lo que querés mostrar

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


class FacturaElectronicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaElectronica
        fields = '__all__'
