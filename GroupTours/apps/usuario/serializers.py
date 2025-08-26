from rest_framework import serializers
from .models import Usuario
from apps.empleado.models import Empleado
from apps.empleado.serializers import EmpleadoSerializer
from apps.rol.models import Rol
from apps.permiso.models import Permiso


class RolSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Rol
        fields = ['id', 'nombre',]


# Serializer resumido para listado
class UsuarioListadoSerializer(serializers.ModelSerializer):
    empleado_id = serializers.IntegerField(source='empleado.id', read_only=True)
    empleado_nombre = serializers.SerializerMethodField()
    empleado_puesto = serializers.SerializerMethodField()
    empleado_email = serializers.SerializerMethodField()
    empleado_telefono = serializers.SerializerMethodField()
    roles = RolSimpleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'empleado_id',
            'empleado_nombre',
            'empleado_puesto',
            'empleado_email',     # nuevo campo
            'empleado_telefono',  # nuevo campo
            'roles',
            'activo',
            'last_login',
            'fecha_creacion',
            'fecha_modificacion'
        ]
    
    def get_empleado_nombre(self, obj):
        if obj.empleado and obj.empleado.persona:
            p = obj.empleado.persona
            if hasattr(p, 'personafisica'):
                pf = p.personafisica
                return f"{pf.nombre} {pf.apellido}"
            if hasattr(p, 'personajuridica'):
                pj = p.personajuridica
                return pj.razon_social
        return None

    def get_empleado_puesto(self, obj):
        if obj.empleado and hasattr(obj.empleado, 'puesto'):
            return obj.empleado.puesto.nombre
        return None

    def get_empleado_email(self, obj):
        if obj.empleado and obj.empleado.persona:
            return getattr(obj.empleado.persona, 'email', None)
        return None

    def get_empleado_telefono(self, obj):
        if obj.empleado and obj.empleado.persona:
            return getattr(obj.empleado.persona, 'telefono', None)
        return None

# Serializer para creación/actualización
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
