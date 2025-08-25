from rest_framework import serializers
from .models import Usuario
from apps.empleado.models import Empleado
from apps.empleado.serializers import EmpleadoSerializer
from apps.rol.models import Rol
from apps.permiso.models import Permiso

class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = ['id', 'nombre',]  # ajusta los campos a tu modelo

class RolSimpleSerializer(serializers.ModelSerializer):
    permisos = PermisoSerializer(many=True, read_only=True)
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'permisos', ]

class UsuarioSerializer(serializers.ModelSerializer):
    empleado = EmpleadoSerializer(read_only=True)
    empleado_id = serializers.PrimaryKeyRelatedField(
        queryset=Empleado.objects.all(),
        source='empleado',
        write_only=True
    )
    roles = RolSimpleSerializer(many=True, read_only=True)
    roles_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Rol.objects.all(),
        source="roles"
    )


    class Meta:
        model = Usuario
        fields = [
            'id', 'username', 'empleado', 'empleado_id',
            'roles', 'roles_ids',
            'activo', 'fecha_creacion', 'fecha_modificacion'
        ]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    empleado = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.all())
    roles = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), many=True)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', 'empleado', 'roles', 'activo']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        password = validated_data.pop('password')
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        usuario.roles.set(roles_data)
        return usuario

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles_data is not None:
            instance.roles.set(roles_data)
        return instance
