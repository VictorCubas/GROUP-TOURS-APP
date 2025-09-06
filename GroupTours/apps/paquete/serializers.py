from rest_framework import serializers
from .models import Paquete

class PaqueteSerializer(serializers.ModelSerializer):
    tipo_paquete_nombre = serializers.CharField(source='tipo_paquete.nombre', read_only=True)
    destino_nombre = serializers.CharField(source='destino.nombre', read_only=True)
    distribuidora_nombre = serializers.CharField(source='distribuidora.nombre', read_only=True)
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Paquete
        fields = [
            'id',
            'nombre',
            'tipo_paquete',
            'tipo_paquete_nombre',
            'destino',
            'destino_nombre',
            'distribuidora',
            'distribuidora_nombre',
            'propio',
            'activo',
            'imagen',       # Campo de imagen para subida
            'imagen_url',   # URL completa de la imagen
            'fecha_creacion',
            'fecha_modificacion'
        ]

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None
