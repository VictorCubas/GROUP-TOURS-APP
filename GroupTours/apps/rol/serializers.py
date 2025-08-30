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
            'en_uso',
            'es_admin'
        ]

    def create(self, validated_data):
        permisos = validated_data.pop('permisos', [])
        es_admin = validated_data.get('es_admin', False)

        rol = Rol.objects.create(**validated_data)

        if es_admin:
            # Si es administrador, asignar TODOS los permisos
            todos_permisos = Permiso.objects.all()
            rol.permisos.set(todos_permisos)
        else:
            rol.permisos.set(permisos)

        return rol

    def update(self, instance, validated_data):
        permisos = validated_data.pop('permisos', None)
        es_admin = validated_data.get('es_admin', instance.es_admin)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if es_admin:
            instance.permisos.set(Permiso.objects.all())
        elif permisos is not None:
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
            'es_admin',  # <-- Nuevo campo
            'fecha_creacion',
            'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']
