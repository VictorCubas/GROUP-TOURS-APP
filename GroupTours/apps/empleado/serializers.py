from rest_framework import serializers
from .models import Empleado
from apps.persona.serializers import PersonaFisicaSerializer, PersonaJuridicaSerializer, PersonaCreateSerializer
from apps.persona.models import Persona
from apps.puesto.models import Puesto
from apps.tipo_remuneracion.models import TipoRemuneracion

class PuestoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Puesto
        fields = ['id', 'nombre']

class TipoRemuneracionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoRemuneracion
        fields = ['id', 'nombre', 'descripcion']

# --- Serializer para lectura ---
class EmpleadoSerializer(serializers.ModelSerializer):
    persona = PersonaCreateSerializer(read_only=True)
    persona_id = serializers.PrimaryKeyRelatedField(
        queryset=Persona.objects.all(),
        source='persona',
        write_only=True
    )
    puesto = PuestoSimpleSerializer(read_only=True)
    puesto_id = serializers.PrimaryKeyRelatedField(
        queryset=Puesto.objects.all(),
        source='puesto',
        write_only=True
    )
    tipo_remuneracion = TipoRemuneracionSimpleSerializer(read_only=True)
    tipo_remuneracion_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoRemuneracion.objects.all(),
        source='tipo_remuneracion',
        write_only=True
    )

    class Meta:
        model = Empleado
        fields = [
            'id', 'persona', 'persona_id',
            'puesto', 'puesto_id',
            'tipo_remuneracion', 'tipo_remuneracion_id',
            'salario', 'porcentaje_comision', 'activo',
            'fecha_creacion', 'fecha_modificacion'
        ]

# --- Serializer para creación/actualización ---
class EmpleadoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        fields = [
            'persona', 'puesto', 'tipo_remuneracion', 'salario', 'porcentaje_comision', 'activo'
        ]
