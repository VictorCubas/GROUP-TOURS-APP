from rest_framework import serializers
from .models import Paquete

from apps.tipo_paquete.models import TipoPaquete
from apps.destino.models import Destino
from apps.distribuidora.models import Distribuidora
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio

# Serializers simples para nested representation
class TipoPaqueteSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoPaquete
        fields = ["id", "nombre"]
        
class MonedaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ["id", "nombre", "simbolo", "codigo"]
        
        
class ServicioSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ["id", "nombre"]

class DestinoNestedSerializer(serializers.ModelSerializer):
    pais = serializers.SerializerMethodField()

    class Meta:
        model = Destino
        fields = ['id', 'nombre', 'pais']

    def get_pais(self, obj):
        if obj.pais:
            return {
                'id': obj.pais.id,
                'nombre': obj.pais.nombre
            }
        return None
        
class DistribuidoraSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribuidora
        fields = ["id", "nombre"]

class PaqueteSerializer(serializers.ModelSerializer):
    tipo_paquete = TipoPaqueteSimpleSerializer(read_only=True)
    destino = DestinoNestedSerializer(read_only=True)
    distribuidora = DistribuidoraSimpleSerializer(read_only=True, allow_null=True)
    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)
    servicios = ServicioSimpleSerializer(many=True, read_only=True)  

    # Para escritura (PUT/PATCH/POST) por ID
    tipo_paquete_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoPaquete.objects.all(),
        write_only=True,
        source='tipo_paquete',
        required=False
    )
    destino_id = serializers.PrimaryKeyRelatedField(
        queryset=Destino.objects.all(),
        write_only=True,
        source='destino',
        required=False
    )
    distribuidora_id = serializers.PrimaryKeyRelatedField(
        queryset=Distribuidora.objects.all(),
        write_only=True,
        source='distribuidora',
        allow_null=True,
        required=False
    )
    moneda_id = serializers.PrimaryKeyRelatedField(
        queryset=Moneda.objects.all(),
        write_only=True,
        source='moneda',
        required=False
    )
    servicios_ids = serializers.PrimaryKeyRelatedField(  # escritura
        queryset=Servicio.objects.all(),
        many=True,
        write_only=True,
        source='servicios',
        required=False
    )

    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Paquete
        fields = [
            'id',
            'nombre',
            'tipo_paquete',      # nested read
            'tipo_paquete_id',   # write only
            'destino',           # nested read
            'destino_id',        # write only
            'distribuidora',     # nested read
            'distribuidora_id',  # write only
            'moneda',     # nested read
            'moneda_id',  # write only
            'servicios',      # lectura
            'servicios_ids',  # escritura
            'precio',
            'sena',
            'fecha_inicio',
            'fecha_fin',
            'personalizado',
            'cantidad_pasajeros',
            'propio',
            'activo',
            'imagen',
            'imagen_url',
            'fecha_creacion',
            'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None