# serializers.py
from rest_framework import serializers
from apps.permiso.models import Permiso
from .models import Rol

# Serializer simple para permisos
class PermisoSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = ['id', 'nombre']

# Serializer para crear/editar roles con permisos por ID
class RolSerializer(serializers.ModelSerializer):
    permisos = PermisoSimpleSerializer(many=True, read_only=True)
    permisos_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permiso.objects.all(),
        write_only=True,
        source='permisos'  # indica que esto llena la relación ManyToMany
    )

    class Meta:
        model = Rol
        fields = [
            'id', 'nombre', 'descripcion', 'permisos', 'permisos_ids',
            'activo', 'en_uso', 'fecha_creacion', 'fecha_modificacion'
        ]