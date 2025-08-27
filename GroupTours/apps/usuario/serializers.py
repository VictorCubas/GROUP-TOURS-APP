from rest_framework import serializers
from .models import Usuario
from apps.empleado.models import Empleado
from apps.empleado.serializers import EmpleadoSerializer
from apps.rol.models import Rol
from apps.permiso.models import Permiso
import random
import string
from django.utils.text import slugify


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
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', 'empleado', 'roles', 'activo']
        extra_kwargs = {
            'username': {'read_only': True},  # no se ingresa manualmente
            'password': {'write_only': True}  # no se muestra nunca
        }

    def generate_username(self, empleado):
        """Genera un username basado en nombre y apellido"""
        persona = empleado.persona
        nombre = ""
        apellido = ""

        if hasattr(persona, 'personafisica'):
            nombre = persona.personafisica.nombre
            apellido = persona.personafisica.apellido
        elif hasattr(persona, 'personajuridica'):
            # Para empresas usar razón social sin espacios
            nombre = persona.personajuridica.razon_social
            apellido = ""

        base_username = slugify(f"{nombre}.{apellido}").replace("-", ".").lower()
        if not base_username:
            base_username = f"user{random.randint(1000,9999)}"

        username = base_username
        counter = 1
        while Usuario.objects.filter(username=username).exists():
            counter += 1
            username = f"{base_username}{counter}"
        return username

    def generate_password(self, length=10):
        """Genera una contraseña aleatoria segura"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choice(characters) for _ in range(length))
    
    
    # def update(self, instance, validated_data):
    #     roles_data = validated_data.pop('roles', None)
    #     password = validated_data.pop('password', None)
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     if password:
    #         instance.set_password(password)
    #     instance.save()
    #     if roles_data is not None:
    #         instance.roles.set(roles_data)
    #     return instance

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        empleado = validated_data.get('empleado')

        # Generar username automáticamente
        username = self.generate_username(empleado)

        # Generar password aleatorio si no se envía
        password = validated_data.pop('password', None)
        if not password:
            password = self.generate_password()

        usuario = Usuario(username=username, **validated_data)
        usuario.set_password(password)
        usuario.save()
        usuario.roles.set(roles_data)

        # Guardamos la contraseña generada en el serializer para devolverla
        usuario.generated_password = password
        return usuario

    def to_representation(self, instance):
        """Sobreescribimos para incluir la contraseña generada en la respuesta de creación"""
        data = super().to_representation(instance)
        if hasattr(instance, 'generated_password'):
            data['generated_password'] = instance.generated_password
        return data