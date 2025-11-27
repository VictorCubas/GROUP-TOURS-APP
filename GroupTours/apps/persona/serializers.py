from rest_framework import serializers
from django.db import models
from datetime import date

from apps.nacionalidad.models import Nacionalidad
from .models import Persona, PersonaFisica, PersonaJuridica
from apps.tipo_documento.models import TipoDocumento


class NacionalidadSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nacionalidad
        fields = ['id', 'nombre', 'codigo_alpha2', ]

class TipoDocumentoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoDocumento
        fields = ['id', 'nombre', 'descripcion',]

class ReservaSimpleSerializer(serializers.Serializer):
    """Serializer simple para mostrar reservas de una persona con días para la salida."""
    id = serializers.IntegerField(read_only=True)
    codigo = serializers.CharField(read_only=True)
    estado = serializers.CharField(read_only=True)
    paquete_nombre = serializers.CharField(source='paquete.nombre', read_only=True)
    salida_fecha = serializers.DateField(source='salida.fecha_salida', read_only=True)
    dias_para_salida = serializers.SerializerMethodField()

    def get_dias_para_salida(self, obj):
        """Calcula los días faltantes para la salida del paquete."""
        if obj.salida and obj.salida.fecha_salida:
            hoy = date.today()
            dias = (obj.salida.fecha_salida - hoy).days
            return dias
        return None

# --- Serializers para lectura ---
class PersonaFisicaSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField()
    edad = serializers.ReadOnlyField()
    tipo_documento = TipoDocumentoSimpleSerializer(read_only=True) #para la recuperacion en el listado
    tipo_documento_id = serializers.PrimaryKeyRelatedField( #para guardar o editar
        queryset=TipoDocumento.objects.all(),
        source='tipo_documento',
        write_only=True
    )

    nacionalidad = NacionalidadSimpleSerializer(read_only=True) #para la recuperacion en el listado
    nacionalidad_id = serializers.PrimaryKeyRelatedField( #para guardar o editar
        queryset=Nacionalidad.objects.all(),
        source='nacionalidad',
        write_only=True
    )

    reservas = serializers.SerializerMethodField()

    class Meta:
        model = PersonaFisica
        fields = [
            'id', 'tipo', 'nombre', 'apellido', 'fecha_nacimiento', 'edad', 'sexo',
            'nacionalidad', 'nacionalidad_id', 'documento', 'email', 'telefono',
            'direccion', 'activo', 'fecha_creacion', 'fecha_modificacion', 'tipo_documento_id',
            'tipo_documento', 'reservas'
        ]

    def get_tipo(self, obj):
        return "fisica"

    def get_reservas(self, obj):
        """Obtiene las reservas de la persona como titular con días para la salida."""
        reservas = obj.reservas_titulares.filter(activo=True).select_related('paquete', 'salida')
        return ReservaSimpleSerializer(reservas, many=True).data

class PersonaJuridicaSerializer(serializers.ModelSerializer):
    tipo = serializers.SerializerMethodField()
    tipo_documento = TipoDocumentoSimpleSerializer(read_only=True) #para la recuperacion en el listado
    tipo_documento_id = serializers.PrimaryKeyRelatedField( #para guardar o editar
        queryset=TipoDocumento.objects.all(),
        source='tipo_documento',
        write_only=True
    )

    class Meta:
        model = PersonaJuridica
        fields = [
            'id', 'tipo', 'razon_social', 'representante', 'tipo_documento',
            'tipo_documento_id',
            'documento', 'email', 'telefono', 'direccion', 'activo',
            'fecha_creacion', 'fecha_modificacion'
        ]

    def get_tipo(self, obj):
        return "juridica"

# --- Serializer para creación y actualización ---
class PersonaCreateSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(
        choices=[('fisica', 'PersonaFisica'), ('juridica', 'PersonaJuridica')],
        write_only=True
    )
    tipo_documento = serializers.PrimaryKeyRelatedField(queryset=TipoDocumento.objects.all())
    documento = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=30)
    direccion = serializers.CharField(max_length=250, allow_blank=True, required=False)
    activo = serializers.BooleanField(default=True)

    # Campos PersonaFisica
    nombre = serializers.CharField(max_length=100, required=False)
    apellido = serializers.CharField(max_length=100, required=False)
    fecha_nacimiento = serializers.DateField(required=False)
    sexo = serializers.ChoiceField(choices=PersonaFisica.GENEROS, required=False)
    nacionalidad = serializers.PrimaryKeyRelatedField(
            queryset=Nacionalidad.objects.all(),
            required=False
        )

    # Campos PersonaJuridica
    razon_social = serializers.CharField(max_length=200, required=False)
    representante = serializers.CharField(max_length=150, required=False, allow_null=True)

    def get_tipo(self, obj):
        """Determine the value of 'tipo' based on the instance type."""
        if isinstance(obj, PersonaFisica):
            return 'fisica'
        elif isinstance(obj, PersonaJuridica):
            return 'juridica'
        return None

    def validate(self, data):
        tipo = data.get('tipo')

        # si es actualización y no mandaron tipo → tomarlo del instance
        if not tipo and self.instance:
            if isinstance(self.instance, PersonaFisica):
                tipo = 'fisica'
            elif isinstance(self.instance, PersonaJuridica):
                tipo = 'juridica'

        if tipo == 'fisica':
            required_fields = ['nombre', 'fecha_nacimiento', 'sexo', 'nacionalidad']
            if not self.instance:  # solo obligatorios en creación
                for field in required_fields:
                    if not data.get(field):
                        raise serializers.ValidationError({field: f"El campo '{field}' es requerido para PersonaFisica"})
        elif tipo == 'juridica':
            required_fields = ['razon_social']
            if not self.instance:  # solo obligatorios en creación
                for field in required_fields:
                    if not data.get(field):
                        raise serializers.ValidationError({field: f"El campo '{field}' es requerido para PersonaJuridica"})
        else:
            raise serializers.ValidationError("Tipo de persona inválido")

        return data


    def create(self, validated_data):
        tipo = validated_data.pop('tipo')
        if tipo == 'fisica':
            return PersonaFisica.objects.create(**validated_data)
        elif tipo == 'juridica':
            return PersonaJuridica.objects.create(**validated_data)
        else:
            raise serializers.ValidationError("Tipo de persona inválido")

    def update(self, instance, validated_data):
        tipo = validated_data.pop('tipo')

        # --- Campos comunes ---
        for attr in ['tipo_documento', 'documento', 'email', 'telefono', 'direccion', 'activo']:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])

        # --- Persona Física ---
        if tipo == 'fisica':
            if not hasattr(instance, "personafisica"):
                raise serializers.ValidationError("La persona no es de tipo física o no permite el cambio de tipo de persona")
            persona_fisica = instance.personafisica
            for attr in ['nombre', 'apellido', 'fecha_nacimiento', 'sexo', 'nacionalidad']:
                if attr in validated_data:
                    setattr(persona_fisica, attr, validated_data[attr])
            persona_fisica.save()

        # --- Persona Jurídica ---
        elif tipo == 'juridica':
            if not hasattr(instance, "personajuridica"):
                raise serializers.ValidationError("La persona no es de tipo jurídica o no permite el cambio de tipo de persona")
            persona_juridica = instance.personajuridica
            for attr in ['razon_social', 'representante']:
                if attr in validated_data:
                    setattr(persona_juridica, attr, validated_data[attr])
            persona_juridica.save()

        else:
            raise serializers.ValidationError("Tipo de persona inválido")

        instance.save()
        return instance


    def to_representation(self, instance):
        """Customize the output representation."""
        representation = super().to_representation(instance)
        representation['tipo'] = self.get_tipo(instance)
        return representation