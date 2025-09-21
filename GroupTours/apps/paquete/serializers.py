from rest_framework import serializers
from .models import Paquete, SalidaPaquete, HistorialPrecioPaquete
from apps.tipo_paquete.models import TipoPaquete
from apps.destino.models import Destino
from apps.distribuidora.models import Distribuidora
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio

# ------------------- Serializers simples / nested -------------------
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
    ciudad = serializers.CharField(source="ciudad.nombre", read_only=True)
    pais = serializers.CharField(source="ciudad.pais.nombre", read_only=True)

    class Meta:
        model = Destino
        fields = ['id', 'ciudad', 'pais']

class DistribuidoraSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribuidora
        fields = ["id", "nombre"]

# ------------------- Serializer de SalidaPaquete -------------------
class SalidaPaqueteSerializer(serializers.ModelSerializer):
    moneda_id = serializers.PrimaryKeyRelatedField(
        queryset=Moneda.objects.all(),
        source='moneda'
    )

    class Meta:
        model = SalidaPaquete
        fields = [
            'fecha_salida',
            'moneda',      # lectura nested
            'moneda_id',   # escritura
            'precio_actual',
            'cupo',
            'activo'
        ]
        read_only_fields = ['moneda']  # lectura de nested moneda

# ------------------- Serializer de Paquete -------------------
class PaqueteSerializer(serializers.ModelSerializer):
    tipo_paquete = TipoPaqueteSimpleSerializer(read_only=True)
    destino = DestinoNestedSerializer(read_only=True)
    distribuidora = DistribuidoraSimpleSerializer(read_only=True, allow_null=True)
    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)
    servicios = ServicioSimpleSerializer(many=True, read_only=True)

    # Escritura por ID
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
    servicios_ids = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(),
        many=True,
        write_only=True,
        source='servicios',
        required=False
    )

    # Nested salidas
    salidas = SalidaPaqueteSerializer(many=True, required=False)

    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Paquete
        fields = [
            'id',
            'nombre',
            'tipo_paquete',
            'tipo_paquete_id',
            'destino',
            'destino_id',
            'distribuidora',
            'distribuidora_id',
            'moneda',
            'moneda_id',
            'servicios',
            'servicios_ids',
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
            'fecha_modificacion',
            'salidas'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None

    # ------------------- Métodos create / update -------------------
    def create(self, validated_data):
        salidas_data = validated_data.pop('salidas', [])
        servicios_data = validated_data.pop('servicios', [])

        paquete = Paquete.objects.create(**validated_data)
        paquete.servicios.set(servicios_data)

        for salida_data in salidas_data:
            moneda = salida_data.pop('moneda', None)
            salida = SalidaPaquete.objects.create(paquete=paquete, **salida_data)
            if moneda:
                salida.moneda = moneda
                salida.save()
            # Inicializa historial de precios
            HistorialPrecioPaquete.objects.create(
                salida=salida,
                precio=salida.precio_actual,
                vigente=True
            )
        return paquete

    def update(self, instance, validated_data):
        salidas_data = validated_data.pop('salidas', [])
        servicios_data = validated_data.pop('servicios', [])

        # Actualiza campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualiza servicios
        instance.servicios.set(servicios_data)

        # Política: reemplaza salidas existentes
        if salidas_data:
            instance.salidas.all().delete()
            for salida_data in salidas_data:
                moneda = salida_data.pop('moneda', None)
                salida = SalidaPaquete.objects.create(paquete=instance, **salida_data)
                if moneda:
                    salida.moneda = moneda
                    salida.save()
                # Inicializa historial de precios
                HistorialPrecioPaquete.objects.create(
                    salida=salida,
                    precio=salida.precio_actual,
                    vigente=True
                )
        return instance
