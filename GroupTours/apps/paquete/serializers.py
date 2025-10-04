from rest_framework import serializers
from .models import (
    Paquete,
    PaqueteServicio,
    SalidaPaquete,
    HistorialPrecioPaquete,
    Temporada
)
from apps.tipo_paquete.models import TipoPaquete
from apps.destino.models import Destino
from apps.distribuidora.models import Distribuidora
from apps.moneda.models import Moneda
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion
import json
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Serializers simples
# ---------------------------------------------------------------------
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
        fields = ["id", "ciudad", "pais"]


class DistribuidoraSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribuidora
        fields = ["id", "nombre"]


# ---------------------------------------------------------------------
# SalidaPaquete Serializer
# ---------------------------------------------------------------------
class SalidaPaqueteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    moneda_id = serializers.PrimaryKeyRelatedField(
        queryset=Moneda.objects.all(),
        source="moneda",
        write_only=True,
        required=True
    )
    temporada_id = serializers.PrimaryKeyRelatedField(
        queryset=Temporada.objects.all(),
        source="temporada",
        write_only=True,
        required=False,
        allow_null=True
    )
    hoteles_ids = serializers.PrimaryKeyRelatedField(
        queryset=Hotel.objects.all(),
        many=True,
        write_only=True,
        source="hoteles",
        required=False
    )
    hoteles = serializers.SerializerMethodField(read_only=True)

    habitacion_fija_id = serializers.PrimaryKeyRelatedField(
        queryset=Habitacion.objects.all(),
        source="habitacion_fija",
        write_only=True,
        required=False,
        allow_null=True
    )
    habitacion_fija = serializers.SerializerMethodField(read_only=True)

    moneda = serializers.SerializerMethodField(read_only=True)
    temporada = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SalidaPaquete
        fields = [
            "id",
            "fecha_salida",
            "fecha_regreso",
            "moneda",
            "moneda_id",
            "temporada",
            "temporada_id",
            "precio_actual",
            "precio_final",
            "ganancia",
            "comision",
            "precio_venta_sugerido_min",
            "precio_venta_sugerido_max",
            "cupo",
            "senia",
            "activo",
            "hoteles",
            "hoteles_ids",
            "habitacion_fija",
            "habitacion_fija_id",
        ]
        read_only_fields = [
            "id",
            "moneda",
            "temporada",
            "precio_actual",
            "precio_final",
            "precio_venta_sugerido_min",
            "precio_venta_sugerido_max",
            "habitacion_fija",
        ]

    def get_moneda(self, obj):
        return (
            {"id": obj.moneda.id, "nombre": getattr(obj.moneda, "nombre", None)}
            if obj.moneda else None
        )

    def get_temporada(self, obj):
        return (
            {"id": obj.temporada.id, "nombre": getattr(obj.temporada, "nombre", None)}
            if obj.temporada else None
        )

    def get_hoteles(self, obj):
        return [{"id": h.id, "nombre": h.nombre} for h in obj.hoteles.all()]

    def get_habitacion_fija(self, obj):
        return (
            {
                "id": obj.habitacion_fija.id,
                "hotel": obj.habitacion_fija.hotel.nombre,
                "tipo": obj.habitacion_fija.tipo,
            }
            if obj.habitacion_fija else None
        )


# ---------------------------------------------------------------------
# PaqueteServicio Serializer
# ---------------------------------------------------------------------
class PaqueteServicioSerializer(serializers.ModelSerializer):
    servicio_id = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.all(),
        source="servicio"
    )
    nombre_servicio = serializers.CharField(
        source="servicio.nombre",
        read_only=True
    )
    precio = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = PaqueteServicio
        fields = ["servicio_id", "nombre_servicio", "precio"]

    def validate_precio(self, value):
        if value in ("", None):
            return Decimal("0")
        return Decimal(value)


# ---------------------------------------------------------------------
# Paquete Serializer
# ---------------------------------------------------------------------
class PaqueteSerializer(serializers.ModelSerializer):
    tipo_paquete = TipoPaqueteSimpleSerializer(read_only=True)
    destino = DestinoNestedSerializer(read_only=True)
    distribuidora = DistribuidoraSimpleSerializer(read_only=True, allow_null=True)
    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)

    servicios = PaqueteServicioSerializer(
        source="paquete_servicios",
        many=True,
        read_only=True
    )

    servicios_data = PaqueteServicioSerializer(
        many=True,
        write_only=True,
        required=False
    )

    tipo_paquete_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoPaquete.objects.all(),
        write_only=True,
        source="tipo_paquete"
    )
    destino_id = serializers.PrimaryKeyRelatedField(
        queryset=Destino.objects.all(),
        write_only=True,
        source="destino"
    )
    distribuidora_id = serializers.PrimaryKeyRelatedField(
        queryset=Distribuidora.objects.all(),
        write_only=True,
        source="distribuidora",
        allow_null=True,
        required=False
    )
    moneda_id = serializers.PrimaryKeyRelatedField(
        queryset=Moneda.objects.all(),
        write_only=True,
        source="moneda",
        required=False
    )

    modalidad = serializers.ChoiceField(
        choices=Paquete.TIPO_SELECCION,
        default=Paquete.FLEXIBLE,
        required=False
    )
    salidas = SalidaPaqueteSerializer(many=True, required=False)

    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()
    precio = serializers.SerializerMethodField()
    senia = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Paquete
        fields = [
            "id",
            "nombre",
            "tipo_paquete",
            "tipo_paquete_id",
            "destino",
            "destino_id",
            "distribuidora",
            "distribuidora_id",
            "moneda",
            "moneda_id",
            "servicios",
            "servicios_data",
            "modalidad",
            "precio",
            "senia",
            "fecha_inicio",
            "fecha_fin",
            "personalizado",
            "cantidad_pasajeros",
            "propio",
            "activo",
            "imagen",
            "imagen_url",
            "fecha_creacion",
            "fecha_modificacion",
            "salidas",
        ]
        read_only_fields = ["fecha_creacion", "fecha_modificacion"]

    # ------------------
    # Parseo de servicios_data desde FormData (JSON string → lista)
    # ------------------
    def _get_servicios_from_initial(self):
        raw = getattr(self, "initial_data", {}).get("servicios_data")
        if not raw:
            return []
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                return data if isinstance(data, list) else []
            except Exception:
                logger.exception("Error parseando servicios_data desde initial_data")
                return []
        if isinstance(raw, list):
            return raw
        return []

    def to_internal_value(self, data):
        data = data.copy()
        servicios_raw = data.get("servicios_data")
        parsed_list = []

        if servicios_raw:
            if isinstance(servicios_raw, str):
                try:
                    parsed = json.loads(servicios_raw)
                    if isinstance(parsed, list):
                        parsed_list = parsed
                except Exception:
                    parsed_list = []
            elif isinstance(servicios_raw, list):
                parsed_list = servicios_raw

        servicios_cleaned = []
        for item in parsed_list:    
            servicio_id = item.get("servicio_id")
            if not servicio_id:
                continue
            servicios_cleaned.append({
                "servicio": servicio_id,  # resolveremos en create/update
                "precio": Decimal(item.get("precio", 0) or 0)
            })

        data["servicios_data"] = servicios_cleaned
        return super().to_internal_value(data)

    # ------------------
    # Validación condicional
    # ------------------
    def validate(self, attrs):
        servicios = attrs.get("servicios_data") or self._get_servicios_from_initial()
        propio = attrs.get("propio", getattr(self.instance, "propio", False))

        if propio and not servicios:
            raise serializers.ValidationError({
                "servicios_data": "Para paquetes propios es obligatorio enviar al menos un servicio."
            })
        return super().validate(attrs)

    # --------- Campos calculados ---------
    def get_fecha_inicio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return salida.fecha_salida if salida else None

    def get_fecha_fin(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("-fecha_regreso").first()
        return salida.fecha_regreso if salida else None

    def get_precio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return salida.precio_actual if salida else None

    def get_senia(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return getattr(salida, "senia", None)

    def get_imagen_url(self, obj):
        request = self.context.get("request")
        if obj.imagen and hasattr(obj.imagen, "url"):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None

    # --------- Helpers ---------
    def _resolve_fk_instance(self, field_name, value, model_class):
        if value is None:
            return None
        if isinstance(value, model_class):
            return value
        pk = value.get("id") if isinstance(value, dict) else value
        try:
            return model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return None

    def _get_salidas_from_initial(self):
        raw = getattr(self, "initial_data", {}).get("salidas")
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

    # --------- Create & Update ---------
    def create(self, validated_data):
        servicios_data = validated_data.pop("servicios_data", None)
        salidas_data = validated_data.pop("salidas", None)

        if servicios_data is None:
            servicios_data = self._get_servicios_from_initial() or []
        if not salidas_data:
            salidas_data = self._get_salidas_from_initial() or []

        paquete = Paquete.objects.create(**validated_data)
    
        # Crear servicios
        for servicio_item in servicios_data:
            servicio_obj = self._resolve_fk_instance("servicio", servicio_item.get("servicio") or servicio_item.get("servicio_id"), Servicio)
            precio_val = Decimal(servicio_item.get("precio", 0) or 0)
            if servicio_obj:
                PaqueteServicio.objects.create(
                    paquete=paquete,
                    servicio=servicio_obj,
                    precio=precio_val
                )

        # Crear salidas
        for salida_data in salidas_data:
            hoteles_ids = salida_data.pop("hoteles", [])
            moneda_val = salida_data.pop("moneda", None) or salida_data.pop("moneda_id", None)
            temporada_val = salida_data.pop("temporada", None) or salida_data.pop("temporada_id", None)
            habitacion_fija_val = salida_data.pop("habitacion_fija", None) or salida_data.pop("habitacion_fija_id", None)

            moneda_obj = self._resolve_fk_instance("moneda", moneda_val, Moneda)
            if not moneda_obj:
                raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

            temporada_obj = self._resolve_fk_instance("temporada", temporada_val, Temporada)
            habitacion_obj = self._resolve_fk_instance("habitacion_fija", habitacion_fija_val, Habitacion)

            salida = SalidaPaquete.objects.create(
                paquete=paquete,
                moneda=moneda_obj,
                temporada=temporada_obj,
                habitacion_fija=habitacion_obj,
                **{k: v for k, v in salida_data.items() if k not in ["hoteles"]}
            )

            if hoteles_ids:
                salida.hoteles.set(hoteles_ids)

            salida.calcular_precio_venta()
            HistorialPrecioPaquete.objects.create(
                salida=salida,
                precio=salida.precio_actual,
                vigente=True,
            )

        return paquete

    def update(self, instance, validated_data):
        servicios_data = validated_data.pop("servicios_data", None)
        salidas_data = validated_data.pop("salidas", None)

        # Actualizar atributos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualizar servicios
        if servicios_data is not None:
            instance.paquete_servicios.all().delete()
            for servicio_item in servicios_data:
                servicio_obj = self._resolve_fk_instance("servicio", servicio_item.get("servicio"), Servicio)
                precio_val = Decimal(servicio_item.get("precio", 0) or 0)
                if servicio_obj:
                    PaqueteServicio.objects.create(
                        paquete=instance,
                        servicio=servicio_obj,
                        precio=precio_val
                    )

        # Actualizar salidas
        if salidas_data is not None:
            salidas_existentes = {s.id: s for s in instance.salidas.all()}
            enviados_ids = []

            for salida_data in salidas_data:
                salida_id = salida_data.get("id")
                hoteles_ids = salida_data.pop("hoteles", [])
                moneda_val = salida_data.pop("moneda", None) or salida_data.pop("moneda_id", None)
                temporada_val = salida_data.pop("temporada", None) or salida_data.pop("temporada_id", None)
                habitacion_fija_val = salida_data.pop("habitacion_fija", None) or salida_data.pop("habitacion_fija_id", None)

                moneda_obj = self._resolve_fk_instance("moneda", moneda_val, Moneda)
                if not moneda_obj:
                    raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

                temporada_obj = self._resolve_fk_instance("temporada", temporada_val, Temporada)
                habitacion_obj = self._resolve_fk_instance("habitacion_fija", habitacion_fija_val, Habitacion)

                if salida_id and salida_id in salidas_existentes:
                    salida = salidas_existentes[salida_id]
                    for attr, value in salida_data.items():
                        setattr(salida, attr, value)

                    salida.moneda = moneda_obj
                    salida.temporada = temporada_obj
                    salida.habitacion_fija = habitacion_obj
                    salida.save()

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

                    enviados_ids.append(salida_id)
                else:
                    salida = SalidaPaquete.objects.create(
                        paquete=instance,
                        moneda=moneda_obj,
                        temporada=temporada_obj,
                        habitacion_fija=habitacion_obj,
                        **{k: v for k, v in salida_data.items() if k not in ["hoteles"]}
                    )

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

                    salida.calcular_precio_venta()
                    HistorialPrecioPaquete.objects.create(
                        salida=salida,
                        precio=salida.precio_actual,
                        vigente=True,
                    )

            # Eliminar las no enviadas
            for s_id, salida in salidas_existentes.items():
                if s_id not in enviados_ids:
                    salida.delete()

        return instance
