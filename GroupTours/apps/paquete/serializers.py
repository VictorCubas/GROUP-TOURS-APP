from rest_framework import serializers
from .models import Paquete, SalidaPaquete, HistorialPrecioPaquete, Temporada
from apps.tipo_paquete.models import TipoPaquete
from apps.destino.models import Destino
from apps.distribuidora.models import Distribuidora
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
import json
import logging

logger = logging.getLogger(__name__)


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
    id = serializers.IntegerField(read_only=True)
    
    moneda_id = serializers.PrimaryKeyRelatedField(
        queryset=Moneda.objects.all(),
        source='moneda',
        write_only=True,
        required=False,
        allow_null=False
    )
    temporada_id = serializers.PrimaryKeyRelatedField(
        queryset=Temporada.objects.all(),
        source='temporada',
        write_only=True,
        required=False,
        allow_null=True
    )

    moneda = serializers.SerializerMethodField(read_only=True)
    temporada = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SalidaPaquete
        fields = [
            'id',
            'fecha_salida',
            'fecha_regreso',   # NUEVO
            'moneda',       
            'moneda_id',    
            'temporada',    
            'temporada_id',
            'precio_actual',
            'cupo',
            'senia',          # NUEVO
            'activo'
        ]
        read_only_fields = ['id', 'moneda', 'temporada']

    def get_moneda(self, obj):
        return {'id': obj.moneda.id, 'nombre': getattr(obj.moneda, 'nombre', None)} if obj.moneda else None

    def get_temporada(self, obj):
        return {'id': obj.temporada.id, 'nombre': getattr(obj.temporada, 'nombre', None)} if obj.temporada else None

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

    # Campos calculados a partir de la salida vigente
    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()
    precio = serializers.SerializerMethodField()
    senia = serializers.SerializerMethodField()

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
            'senia',
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

    # -------------------- Campos calculados --------------------
    def get_fecha_inicio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        return salida.fecha_salida if salida else None

    def get_fecha_fin(self, obj):
        salida = obj.salidas.filter(activo=True).order_by('-fecha_regreso').first()
        return salida.fecha_regreso if salida else None

    def get_precio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        return salida.precio_actual if salida else None

    def get_senia(self, obj):
        salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        return getattr(salida, "senia", None)

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and hasattr(obj.imagen, 'url'):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None

    # -------------------- Helpers --------------------
    def _resolve_fk_instance(self, field_name, value, model_class):
        if value is None:
            return None
        if isinstance(value, model_class):
            return value
        pk = value.get('id') if isinstance(value, dict) else value
        try:
            return model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return None

    def _get_salidas_from_initial(self):
        raw = getattr(self, 'initial_data', {}).get('salidas')
        if not raw:
            return []
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                return data if isinstance(data, list) else []
            except Exception:
                logger.exception("Error parseando salidas desde initial_data")
                return []
        if isinstance(raw, list):
            return raw
        return []

    # -------------------- Create & Update --------------------
    def create(self, validated_data):
        salidas_data = validated_data.pop('salidas', None)
        servicios_data = validated_data.pop('servicios', [])

        if not salidas_data:
            salidas_data = self._get_salidas_from_initial() or []

        paquete = Paquete.objects.create(**validated_data)

        if servicios_data:
            paquete.servicios.set(servicios_data)

        for salida_data in salidas_data:
            moneda_val = salida_data.pop('moneda', None) or salida_data.pop('moneda_id', None)
            temporada_val = salida_data.pop('temporada', None) or salida_data.pop('temporada_id', None)

            moneda_obj = self._resolve_fk_instance('moneda', moneda_val, Moneda)
            if not moneda_obj:
                raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

            temporada_obj = self._resolve_fk_instance('temporada', temporada_val, Temporada)

            salida_data['moneda'] = moneda_obj
            if temporada_obj:
                salida_data['temporada'] = temporada_obj

            salida = SalidaPaquete.objects.create(paquete=paquete, **salida_data)

            HistorialPrecioPaquete.objects.create(
                salida=salida,
                precio=salida.precio_actual,
                vigente=True
            )

        return paquete

    def update(self, instance, validated_data):
        salidas_data = validated_data.pop('salidas', None)
        servicios_data = validated_data.pop('servicios', [])

        if not salidas_data:
            salidas_data = self._get_salidas_from_initial() or []

        # Actualiza campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if servicios_data:
            instance.servicios.set(servicios_data)

        if salidas_data is not None:
            salidas_existentes = {s.id: s for s in instance.salidas.all()}
            enviados_ids = []

            for salida_data in salidas_data:
                salida_id = salida_data.get('id')
                moneda_val = salida_data.pop('moneda', None) or salida_data.pop('moneda_id', None)
                temporada_val = salida_data.pop('temporada', None) or salida_data.pop('temporada_id', None)

                moneda_obj = self._resolve_fk_instance('moneda', moneda_val, Moneda)
                if not moneda_obj:
                    raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

                temporada_obj = self._resolve_fk_instance('temporada', temporada_val, Temporada)

                salida_data['moneda'] = moneda_obj
                if temporada_obj:
                    salida_data['temporada'] = temporada_obj

                if salida_id and salida_id in salidas_existentes:
                    salida = salidas_existentes[salida_id]
                    for attr, value in salida_data.items():
                        setattr(salida, attr, value)
                    salida.save()
                    enviados_ids.append(salida_id)
                else:
                    salida = SalidaPaquete.objects.create(paquete=instance, **salida_data)

                HistorialPrecioPaquete.objects.create(
                    salida=salida,
                    precio=salida.precio_actual,
                    vigente=True
                )

            # Eliminar salidas que no fueron enviadas (opcional)
            for s_id, salida in salidas_existentes.items():
                if s_id not in enviados_ids:
                    salida.delete()

        return instance
