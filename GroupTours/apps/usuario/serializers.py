# apps/usuario/serializers.py
from rest_framework import serializers
from .models import Usuario
from apps.empleado.models import Empleado
from apps.rol.models import Rol
import random
import string
from django.utils.text import slugify

class RolSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre']

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
            'empleado_email',
            'empleado_telefono',
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
                return f"{p.personafisica.nombre} {p.personafisica.apellido}"
            if hasattr(p, 'personajuridica'):
                return p.personajuridica.razon_social
        return None

    def get_empleado_puesto(self, obj):
        return getattr(obj.empleado.puesto, 'nombre', None) if obj.empleado else None

    def get_empleado_email(self, obj):
        return getattr(obj.empleado.persona, 'email', None) if obj.empleado else None

    def get_empleado_telefono(self, obj):
        return getattr(obj.empleado.persona, 'telefono', None) if obj.empleado else None

class UsuarioCreateSerializer(serializers.ModelSerializer):
    empleado = serializers.PrimaryKeyRelatedField(queryset=Empleado.objects.all())
    roles = serializers.PrimaryKeyRelatedField(queryset=Rol.objects.all(), many=True)
    password = serializers.CharField(write_only=True, required=False)  # No es obligatorio

    class Meta:
        model = Usuario
        fields = ['id', 'username', 'password', 'empleado', 'roles', 'activo']
        extra_kwargs = {
            'username': {'read_only': True},  # Autogenerado
            'password': {'write_only': True}
        }

    def generate_username(self, empleado):
        persona = empleado.persona
        nombre = ""
        apellido = ""

        if hasattr(persona, 'personafisica'):
            nombre = persona.personafisica.nombre
            apellido = persona.personafisica.apellido
        elif hasattr(persona, 'personajuridica'):
            nombre = persona.personajuridica.razon_social

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
        characters = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(random.choice(characters) for _ in range(length))
    
    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        empleado = validated_data.get('empleado')

        username = self.generate_username(empleado)
        password = validated_data.pop('password', None) or self.generate_password()

        usuario = Usuario(username=username, **validated_data)
        usuario.set_password(password)
        usuario.save()
        usuario.roles.set(roles_data)

        usuario.generated_password = password  # Para devolverla en la respuesta
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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if hasattr(instance, 'generated_password'):
            data['generated_password'] = instance.generated_password
        return data
