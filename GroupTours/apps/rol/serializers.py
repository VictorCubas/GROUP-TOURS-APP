from rest_framework import serializers

from apps.permiso.models import Permiso
from .models import Rol, RolesPermisos
from apps.permiso.serializers import PermisoSerializer, ModuloSimpleSerializer  # Para incluir info de permisos


class PermisoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = ['id', 'nombre']  # Solo id y nombre

class RolCreateUpdateSerializer(serializers.ModelSerializer):
    permisos_id = serializers.PrimaryKeyRelatedField(
        queryset=Permiso.objects.all(),
        many=True,
        source='permisos'  # esto enlaza con el campo ManyToMany
    )

    class Meta:
        model = Rol
        fields = [
            'id',
            'nombre',
            'descripcion',
            'permisos_id',
            'activo',
            'en_uso'
        ]

    def create(self, validated_data):
        permisos = validated_data.pop('permisos', [])
        rol = Rol.objects.create(**validated_data)
        rol.permisos.set(permisos)
        return rol

    def update(self, instance, validated_data):
        permisos = validated_data.pop('permisos', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if permisos is not None:
            instance.permisos.set(permisos)
        return instance


class RolSerializer(serializers.ModelSerializer):
    # Para mostrar los permisos asociados de forma detallada
    permisos = PermisoSimpleSerializer(many=True, read_only=True)

    class Meta:
        model = Rol
        fields = [
            'id',
            'nombre',
            'descripcion',
            'permisos',
            'activo',
            'en_uso',
            'fecha_creacion',
            'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
