from rest_framework import serializers
from .models import (
    CupoHabitacionSalida,
    ItemCostoPaquete,
    ItemCostoSalida,
    Paquete,
    PaqueteServicio,
    PrecioCatalogoHotel,
    PrecioCatalogoHabitacion,
    SalidaPaquete,
    HistorialPrecioPaquete,
    Temporada,
    TipoCostoSalida,
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
    # zona_geografica = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Destino
        fields = ["id", "ciudad", "pais", ]

    # def get_zona_geografica(self, obj):
    #     """
    #     Retorna la zona geográfica asociada al país de la ciudad, si existe.
    #     Formato: { "id": .., "nombre": .., "descripcion": .. } o None.
    #     """
    #     try:
    #         zona = obj.ciudad.pais.zona_geografica
    #         if not zona:
    #             return None
    #         # si la zona tiene descripción, la incluimos; si no, devolvemos solo id/nombre
    #         return {
    #             "id": zona.id,
    #             "nombre": getattr(zona, "nombre", None),
    #             "descripcion": getattr(zona, "descripcion", None)
    #         }
    #     except Exception:
    #         return None


class DistribuidoraSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distribuidora
        fields = ["id", "nombre"]


# ---------------------------------------------------------------------
# CupoHabitacionSalida Serializer
# ---------------------------------------------------------------------
class CupoHabitacionSalidaSerializer(serializers.ModelSerializer):
    habitacion_id = serializers.PrimaryKeyRelatedField(
        queryset=Habitacion.objects.all(),
        source="habitacion",
        write_only=True
    )
    habitacion = serializers.SerializerMethodField(read_only=True)
    cupo = serializers.IntegerField(required=True)

    class Meta:
        model = CupoHabitacionSalida
        fields = ["habitacion", "habitacion_id", "cupo"]

    def get_habitacion(self, obj):
        return {
            "id": obj.habitacion.id,
            "tipo_habitacion": obj.habitacion.tipo_habitacion.nombre,
            "capacidad": obj.habitacion.tipo_habitacion.capacidad,
            "hotel": obj.habitacion.hotel.nombre,
        }


# ---------------------------------------------------------------------
# PrecioCatalogoHotel Serializer
# ---------------------------------------------------------------------
class PrecioCatalogoHotelSerializer(serializers.ModelSerializer):
    hotel_id = serializers.PrimaryKeyRelatedField(
        queryset=Hotel.objects.all(),
        source="hotel",
        write_only=True
    )
    hotel = serializers.SerializerMethodField(read_only=True)
    precio_catalogo = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    class Meta:
        model = PrecioCatalogoHotel
        fields = ["hotel", "hotel_id", "precio_catalogo"]

    def get_hotel(self, obj):
        return {
            "id": obj.hotel.id,
            "nombre": obj.hotel.nombre,
        }


# ---------------------------------------------------------------------
# PrecioCatalogoHabitacion Serializer
# ---------------------------------------------------------------------
class PrecioCatalogoHabitacionSerializer(serializers.ModelSerializer):
    habitacion_id = serializers.PrimaryKeyRelatedField(
        queryset=Habitacion.objects.all(),
        source="habitacion",
        write_only=True
    )
    habitacion = serializers.SerializerMethodField(read_only=True)
    precio_catalogo = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)

    class Meta:
        model = PrecioCatalogoHabitacion
        fields = ["habitacion", "habitacion_id", "precio_catalogo"]

    def get_habitacion(self, obj):
        return {
            "id": obj.habitacion.id,
            "tipo_habitacion": obj.habitacion.tipo_habitacion.nombre,
            "capacidad": obj.habitacion.tipo_habitacion.capacidad,
            "hotel": obj.habitacion.hotel.nombre,
        }


# ---------------------------------------------------------------------
# TipoCostoSalida Serializer
# ---------------------------------------------------------------------
class TipoCostoSalidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCostoSalida
        fields = ["id", "codigo", "nombre", "dividir_por_pasajeros", "activo"]


# ---------------------------------------------------------------------
# ItemCostoPaquete Serializer
# ---------------------------------------------------------------------
class ItemCostoPaqueteSerializer(serializers.ModelSerializer):
    tipo_costo_id = serializers.PrimaryKeyRelatedField(
        queryset=TipoCostoSalida.objects.all(),
        source="tipo_costo",
        write_only=True
    )
    tipo_costo = TipoCostoSalidaSerializer(read_only=True)

    class Meta:
        model = ItemCostoPaquete
        fields = ["id", "tipo_costo", "tipo_costo_id", "monto", "activo"]


# ---------------------------------------------------------------------
# ItemCostoSalida Serializer (detalle en respuesta de salida)
# ---------------------------------------------------------------------
class ItemCostoSalidaDetalleSerializer(serializers.Serializer):
    """
    Serializer de lectura para ítems de costo en la respuesta de una salida.
    Incluye el campo 'origen' para indicar si el monto viene del paquete o es un override.
    """
    tipo_costo_id = serializers.IntegerField(source="tipo_costo.id")
    nombre = serializers.CharField(source="tipo_costo.nombre")
    dividir_por_pasajeros = serializers.BooleanField(source="tipo_costo.dividir_por_pasajeros")
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    monto_por_pasajero = serializers.SerializerMethodField()
    origen = serializers.CharField()

    def get_monto_por_pasajero(self, obj):
        cupo = obj.get("cupo") or 1
        monto = obj.get("monto") or Decimal("0")
        if obj.get("dividir_por_pasajeros"):
            return monto / Decimal(str(cupo))
        return monto


# ---------------------------------------------------------------------
# SalidaPaquete Serializer
# ---------------------------------------------------------------------
class SalidaPaqueteActualizarFechasSerializer(serializers.ModelSerializer):
    """
    Serializer específico para actualizar solo las fechas de una salida.
    """
    class Meta:
        model = SalidaPaquete
        fields = ['id', 'fecha_salida', 'fecha_regreso']
        read_only_fields = ['id']

    def validate(self, attrs):
        fecha_salida = attrs.get('fecha_salida', self.instance.fecha_salida if self.instance else None)
        fecha_regreso = attrs.get('fecha_regreso', self.instance.fecha_regreso if self.instance else None)
        if fecha_salida and fecha_regreso and fecha_regreso <= fecha_salida:
            raise serializers.ValidationError({
                "fecha_regreso": "La fecha de regreso debe ser posterior a la fecha de salida."
            })
        return attrs


class SalidaPaqueteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    paquete_id = serializers.PrimaryKeyRelatedField(
        queryset=Paquete.objects.all(),
        source="paquete",
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

    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)
    temporada = serializers.SerializerMethodField(read_only=True)

    cupos_habitaciones = CupoHabitacionSalidaSerializer(many=True, read_only=True)
    precios_catalogo_hoteles = PrecioCatalogoHotelSerializer(many=True, read_only=True)
    precios_catalogo_habitaciones = PrecioCatalogoHabitacionSerializer(many=True, read_only=True)

    # Campos calculados para precio total (hotel + ganancia/comisión + servicios)
    precio_venta_total_min = serializers.SerializerMethodField(read_only=True)
    precio_venta_total_max = serializers.SerializerMethodField(read_only=True)

    # Campo para mostrar en moneda alternativa (USD si está en PYG, o PYG si está en USD)
    precio_moneda_alternativa = serializers.SerializerMethodField(read_only=True)

    # Ítems de costo operativo (bus, coordinador, tasas, etc.) — solo paquetes propios
    items_costo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SalidaPaquete
        fields = [
            "id",
            "paquete_id",
            "codigo",
            "fecha_salida",
            "fecha_regreso",
            "moneda",
            "temporada",
            "temporada_id",
            "costo_base_desde",
            "costo_base_hasta",
            "ganancia",
            "comision",
            "precio_venta_sugerido_min",
            "precio_venta_sugerido_max",
            "precio_venta_total_min",
            "precio_venta_total_max",
            "cupo",
            "senia",
            "precio_moneda_alternativa",
            "items_costo",
            "activo",
            "hoteles",
            "hoteles_ids",
            "habitacion_fija",
            "habitacion_fija_id",
            "cupos_habitaciones",
            "precios_catalogo_hoteles",
            "precios_catalogo_habitaciones",
        ]
        read_only_fields = [
            "id",
            "moneda",
            "temporada",
            "costo_base_desde",
            "costo_base_hasta",
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
                "tipo_habitacion": obj.habitacion_fija.tipo_habitacion.nombre,
            }
            if obj.habitacion_fija else None
        )

    def get_precio_venta_total_min(self, obj):
        """
        Retorna el precio de venta total mínimo por pasajero.

        Este valor ya está calculado en precio_venta_sugerido_min e incluye:
        - Precio de habitación (costo_base_desde)
        - Servicios del paquete
        - Ganancia/comisión aplicada

        No se deben sumar los servicios nuevamente ya que precio_venta_sugerido_min
        ya los incluye (calculado en SalidaPaquete.calcular_precio_venta()).
        """
        return obj.precio_venta_sugerido_min or Decimal("0")

    def get_precio_venta_total_max(self, obj):
        """
        Retorna el precio de venta total máximo por pasajero.

        Este valor ya está calculado en precio_venta_sugerido_max e incluye:
        - Precio de habitación (costo_base_hasta)
        - Servicios del paquete
        - Ganancia/comisión aplicada

        No se deben sumar los servicios nuevamente ya que precio_venta_sugerido_max
        ya los incluye (calculado en SalidaPaquete.calcular_precio_venta()).
        """
        return obj.precio_venta_sugerido_max or Decimal("0")

    def get_items_costo(self, obj):
        """
        Devuelve los ítems de costo activos resolviendo la lógica template+override.
        'origen': 'paquete' → viene del default del paquete (📦)
        'origen': 'override' → fue personalizado para esta salida (✏️)
        """
        if not obj.paquete.propio:
            return []

        resultado = []
        cupo = obj.cupo or 1

        for item_default in obj.paquete.items_costo_default.filter(activo=True).select_related("tipo_costo"):
            tipo_costo = item_default.tipo_costo
            if not tipo_costo.activo:
                continue

            override = obj.items_costo.filter(tipo_costo=tipo_costo, activo=True).first()

            if override:
                monto = override.monto
                origen = "override"
            else:
                monto = item_default.monto
                origen = "paquete"

            monto_por_pasajero = (
                monto / Decimal(str(cupo)) if tipo_costo.dividir_por_pasajeros else monto
            )

            resultado.append({
                "tipo_costo_id": tipo_costo.id,
                "nombre": tipo_costo.nombre,
                "dividir_por_pasajeros": tipo_costo.dividir_por_pasajeros,
                "monto": monto,
                "monto_por_pasajero": monto_por_pasajero,
                "origen": origen,
            })

        return resultado

    # ========== MÉTODO PARA MOSTRAR EN MONEDA ALTERNATIVA ==========

    def get_precio_moneda_alternativa(self, obj):
        """
        Retorna precios en la moneda alternativa para mostrar al cliente.
        - Si salida en PYG → muestra en USD
        - Si salida en USD → muestra en PYG

        Esto permite el caso de uso:
        Cliente: "¿Cuánto cuesta?"
        Agente: "El paquete cuesta USD 500" (o "Gs 3,650,000")
        Cliente: "¿Y en la otra moneda?"
        Agente: "Al cambio de hoy, Gs 3,650,000" (o "USD 500")
        """
        try:
            datos = obj.obtener_precio_en_moneda_alternativa()
            return {
                'moneda': datos['moneda_alternativa'],
                'costo_base_desde': datos['precio_min'],
                'costo_base_hasta': datos['precio_max'],
                'precio_venta_min': datos['precio_venta_min'],
                'precio_venta_max': datos['precio_venta_max'],
                'senia': datos['senia'],
                'cotizacion': datos['cotizacion_aplicada'],
                'fecha_cotizacion': datos['fecha_cotizacion']
            }
        except Exception:
            return None

    # ========== CREATE ==========

    def create(self, validated_data):
        from .models import create_salida_paquete

        paquete = validated_data.pop("paquete")
        hoteles = validated_data.pop("hoteles", [])
        temporada = validated_data.pop("temporada", None)
        habitacion_fija = validated_data.pop("habitacion_fija", None)
        activo = validated_data.get("activo", True)

        # Estos campos son read_only en el serializer, se leen del raw data
        raw = self.initial_data
        cupos_habitaciones_data = raw.get("cupos_habitaciones", [])
        precios_catalogo_hoteles_data = raw.get("precios_catalogo_hoteles", [])
        precios_catalogo_habitaciones_data = raw.get("precios_catalogo_habitaciones", [])
        items_costo_override_data = raw.get("items_costo_override_data", None)

        data = {
            "paquete_id": paquete.id,
            "moneda_id": paquete.moneda_id,
            "hoteles_ids": [h.id for h in hoteles],
            "fecha_salida": validated_data["fecha_salida"],
            "fecha_regreso": validated_data.get("fecha_regreso"),
            "cupo": validated_data.get("cupo", 0),
            "senia": validated_data.get("senia"),
            "ganancia": validated_data.get("ganancia"),
            "comision": validated_data.get("comision"),
        }

        salida = create_salida_paquete(data)

        # Cupos por habitación (solo paquetes propios)
        if paquete.propio:
            for cupo_item in cupos_habitaciones_data:
                habitacion_obj = self._resolve_fk_instance(
                    cupo_item.get("habitacion") or cupo_item.get("habitacion_id"), Habitacion
                )
                if habitacion_obj:
                    CupoHabitacionSalida.objects.create(
                        salida=salida,
                        habitacion=habitacion_obj,
                        cupo=cupo_item.get("cupo", 0)
                    )

        # Precios de catálogo por hotel (propios y distribuidoras)
        for precio_item in precios_catalogo_hoteles_data:
            hotel_obj = self._resolve_fk_instance(
                precio_item.get("hotel") or precio_item.get("hotel_id"), Hotel
            )
            if hotel_obj:
                precio_catalogo_hotel = Decimal(precio_item.get("precio_catalogo", 0) or 0)
                PrecioCatalogoHotel.objects.create(
                    salida=salida,
                    hotel=hotel_obj,
                    precio_catalogo=precio_catalogo_hotel
                )
                # Crear precio individual para cada habitación activa del hotel
                for habitacion in Habitacion.objects.filter(hotel=hotel_obj, activo=True):
                    PrecioCatalogoHabitacion.objects.get_or_create(
                        salida=salida,
                        habitacion=habitacion,
                        defaults={"precio_catalogo": precio_catalogo_hotel}
                    )

        # Precios de catálogo por habitación (pueden sobrescribir los del hotel)
        for precio_item in precios_catalogo_habitaciones_data:
            habitacion_obj = self._resolve_fk_instance(
                precio_item.get("habitacion") or precio_item.get("habitacion_id"), Habitacion
            )
            if habitacion_obj:
                PrecioCatalogoHabitacion.objects.update_or_create(
                    salida=salida,
                    habitacion=habitacion_obj,
                    defaults={"precio_catalogo": Decimal(precio_item.get("precio_catalogo", 0) or 0)}
                )

        # Recalcular costo_base_desde/hasta desde precios de catálogo en BD
        precios_habitacion_bd = salida.precios_catalogo_habitaciones.all()
        if precios_habitacion_bd.exists():
            precios_list = [pc.precio_catalogo for pc in precios_habitacion_bd]
            salida.costo_base_desde = min(precios_list)
            salida.costo_base_hasta = max(precios_list)
            salida.save(update_fields=["costo_base_desde", "costo_base_hasta"])

        # Ítems de costo override por salida (opcional)
        if items_costo_override_data is not None:
            for item in items_costo_override_data:
                tipo_costo_id = item.get("tipo_costo_id")
                if not tipo_costo_id:
                    continue
                try:
                    tipo_costo_obj = TipoCostoSalida.objects.get(id=tipo_costo_id, activo=True)
                except TipoCostoSalida.DoesNotExist:
                    continue
                ItemCostoSalida.objects.create(
                    salida=salida,
                    tipo_costo=tipo_costo_obj,
                    monto=Decimal(str(item.get("monto", 0) or 0))
                )

        # Calcular precio de venta sugerido desde catálogo
        salida.calcular_precio_venta()

        # Registrar precio inicial en historial
        HistorialPrecioPaquete.objects.create(
            salida=salida,
            precio=salida.costo_base_desde,
            vigente=True,
        )

        update_fields = []
        if temporada:
            salida.temporada = temporada
            update_fields.append("temporada")
        if habitacion_fija:
            salida.habitacion_fija = habitacion_fija
            update_fields.append("habitacion_fija")
        if not activo:
            salida.activo = False
            update_fields.append("activo")
        if update_fields:
            salida.save(update_fields=update_fields)

        return salida

    # ========== UPDATE ==========

    def update(self, instance, validated_data):
        raw = self.initial_data
        hoteles = validated_data.pop("hoteles", [])
        temporada = validated_data.pop("temporada", None)
        habitacion_fija = validated_data.pop("habitacion_fija", None)

        cupos_habitaciones_data       = raw.get("cupos_habitaciones", []) or []
        precios_catalogo_hoteles_data = raw.get("precios_catalogo_hoteles", []) or []
        precios_catalogo_hab_data     = raw.get("precios_catalogo_habitaciones", []) or []
        items_costo_override_data     = raw.get("items_costo_override_data", None)

        # --- Campos planos ---
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if temporada is not None:
            instance.temporada = temporada
        if habitacion_fija is not None:
            instance.habitacion_fija = habitacion_fija
        instance.save()

        # --- Hoteles ---
        if hoteles:
            instance.hoteles.set(hoteles)

        # --- Cupos por habitación (solo propios) ---
        if instance.paquete.propio and cupos_habitaciones_data:
            enviados_habitaciones = []
            for cupo_item in cupos_habitaciones_data:
                hab_id = cupo_item.get("habitacion_id") or (
                    cupo_item.get("habitacion", {}).get("id")
                    if isinstance(cupo_item.get("habitacion"), dict) else None
                )
                hab_obj = self._resolve_fk_instance(hab_id, Habitacion)
                if not hab_obj:
                    continue
                CupoHabitacionSalida.objects.update_or_create(
                    salida=instance,
                    habitacion=hab_obj,
                    defaults={"cupo": cupo_item.get("cupo", 0)}
                )
                enviados_habitaciones.append(hab_obj.id)
            instance.cupos_habitaciones.exclude(
                habitacion__id__in=enviados_habitaciones
            ).delete()

        # --- Precios por hotel (propios y distribuidoras) ---
        enviados_precios_hoteles = []
        habitaciones_actualizadas_por_hotel = set()

        for precio_item in precios_catalogo_hoteles_data:
            hotel_id = precio_item.get("hotel_id") or (
                precio_item.get("hotel", {}).get("id")
                if isinstance(precio_item.get("hotel"), dict) else None
            )
            hotel_obj = self._resolve_fk_instance(hotel_id, Hotel)
            if not hotel_obj:
                continue
            precio_hotel = Decimal(precio_item.get("precio_catalogo", 0) or 0)
            PrecioCatalogoHotel.objects.update_or_create(
                salida=instance,
                hotel=hotel_obj,
                defaults={"precio_catalogo": precio_hotel}
            )
            enviados_precios_hoteles.append(hotel_obj.id)
            for hab in Habitacion.objects.filter(hotel=hotel_obj, activo=True):
                PrecioCatalogoHabitacion.objects.update_or_create(
                    salida=instance,
                    habitacion=hab,
                    defaults={"precio_catalogo": precio_hotel}
                )
                habitaciones_actualizadas_por_hotel.add(hab.id)

        if precios_catalogo_hoteles_data:
            # Fix: capturar hoteles eliminados ANTES del delete
            hoteles_eliminados = list(
                instance.precios_catalogo_hoteles
                .exclude(hotel__id__in=enviados_precios_hoteles)
                .values_list("hotel_id", flat=True)
            )
            instance.precios_catalogo_hoteles.exclude(
                hotel__id__in=enviados_precios_hoteles
            ).delete()
            if hoteles_eliminados:
                habs_a_eliminar = Habitacion.objects.filter(
                    hotel_id__in=hoteles_eliminados
                ).values_list("id", flat=True)
                PrecioCatalogoHabitacion.objects.filter(
                    salida=instance,
                    habitacion_id__in=habs_a_eliminar
                ).delete()

        # --- Precios por habitación (sobrescriben el precio del hotel) ---
        enviados_precios_habs = []
        for precio_item in precios_catalogo_hab_data:
            hab_id = precio_item.get("habitacion_id") or (
                precio_item.get("habitacion", {}).get("id")
                if isinstance(precio_item.get("habitacion"), dict) else None
            )
            hab_obj = self._resolve_fk_instance(hab_id, Habitacion)
            if not hab_obj:
                continue
            PrecioCatalogoHabitacion.objects.update_or_create(
                salida=instance,
                habitacion=hab_obj,
                defaults={"precio_catalogo": Decimal(precio_item.get("precio_catalogo", 0) or 0)}
            )
            enviados_precios_habs.append(hab_obj.id)

        if precios_catalogo_hab_data or precios_catalogo_hoteles_data:
            habs_a_mantener = set(enviados_precios_habs) | habitaciones_actualizadas_por_hotel
            hoteles_en_payload = set(enviados_precios_hoteles)
            if enviados_precios_habs:
                hoteles_en_payload |= set(
                    Habitacion.objects.filter(id__in=enviados_precios_habs)
                    .values_list("hotel_id", flat=True)
                )
            instance.precios_catalogo_habitaciones.filter(
                habitacion__hotel_id__in=hoteles_en_payload
            ).exclude(habitacion__id__in=habs_a_mantener).delete()

        # --- Ítems de costo override (None = no tocar, [] = borrar todos) ---
        if items_costo_override_data is not None:
            existentes = {ics.tipo_costo_id: ics for ics in instance.items_costo.all()}
            enviados_ids = []
            for item in items_costo_override_data:
                tipo_costo_id = item.get("tipo_costo_id")
                if not tipo_costo_id:
                    continue
                try:
                    tipo_costo_obj = TipoCostoSalida.objects.get(id=tipo_costo_id, activo=True)
                except TipoCostoSalida.DoesNotExist:
                    continue
                monto = Decimal(str(item.get("monto", 0) or 0))
                if tipo_costo_obj.id in existentes:
                    ics = existentes[tipo_costo_obj.id]
                    if ics.monto != monto:
                        ics.monto = monto
                        ics.save()
                else:
                    ItemCostoSalida.objects.create(
                        salida=instance,
                        tipo_costo=tipo_costo_obj,
                        monto=monto
                    )
                enviados_ids.append(tipo_costo_obj.id)
            instance.items_costo.exclude(tipo_costo_id__in=enviados_ids).delete()

        # --- Recalcular precios ---
        precios_bd = instance.precios_catalogo_habitaciones.all()
        if precios_bd.exists():
            precios_list = [pc.precio_catalogo for pc in precios_bd]
            instance.costo_base_desde = min(precios_list)
            instance.costo_base_hasta = max(precios_list)
            instance.save(update_fields=["costo_base_desde", "costo_base_hasta"])

        instance.calcular_precio_venta()

        return instance

    def _resolve_fk_instance(self, pk, model_class):
        if pk is None:
            return None
        if isinstance(pk, model_class):
            return pk
        try:
            return model_class.objects.get(pk=pk)
        except model_class.DoesNotExist:
            return None


# ---------------------------------------------------------------------
# SalidaPaquete - Serializer liviano para LISTADO
# ---------------------------------------------------------------------
class SalidaPaqueteListSerializer(serializers.ModelSerializer):
    """
    Serializer liviano para el listado de salidas.
    Incluye datos de paquete, moneda, cupos y stats de reservas.
    Los campos cupo_total y cupo_disponible se toman de anotaciones en el queryset.
    """
    paquete_id = serializers.IntegerField(source="paquete.id", read_only=True)
    paquete_nombre = serializers.CharField(source="paquete.nombre", read_only=True)
    paquete_propio = serializers.BooleanField(source="paquete.propio", read_only=True)
    destino = serializers.SerializerMethodField()
    moneda = MonedaSimpleSerializer(read_only=True)

    cupo_disponible = serializers.IntegerField(source="cupo", read_only=True)
    cupo_total = serializers.SerializerMethodField()
    total_reservas = serializers.SerializerMethodField()
    dias_hasta_salida = serializers.SerializerMethodField()

    class Meta:
        model = SalidaPaquete
        fields = [
            "id",
            "codigo",
            "paquete_id",
            "paquete_nombre",
            "paquete_propio",
            "destino",
            "moneda",
            "fecha_salida",
            "fecha_regreso",
            "dias_hasta_salida",
            "costo_base_desde",
            "costo_base_hasta",
            "precio_venta_sugerido_min",
            "precio_venta_sugerido_max",
            "senia",
            "cupo_disponible",
            "cupo_total",
            "total_reservas",
            "activo",
        ]

    def get_destino(self, obj):
        try:
            destino = obj.paquete.destino
            return {
                "id": destino.id,
                "ciudad": destino.ciudad.nombre if destino.ciudad else None,
                "pais": destino.ciudad.pais.nombre if destino.ciudad and destino.ciudad.pais else None,
            }
        except Exception:
            return None

    def get_cupo_total(self, obj):
        """Cupo original = cupo disponible + pasajeros de reservas activas no canceladas."""
        cupo_disponible = obj.cupo or 0
        cupo_ocupado = sum(
            r.cantidad_pasajeros or 0
            for r in obj.reservas.filter(activo=True).exclude(estado="cancelada")
        )
        return cupo_disponible + cupo_ocupado

    def get_total_reservas(self, obj):
        return obj.reservas.filter(activo=True).exclude(estado="cancelada").count()

    def get_dias_hasta_salida(self, obj):
        if not obj.fecha_salida:
            return None
        from django.utils.timezone import now
        return (obj.fecha_salida - now().date()).days


# ---------------------------------------------------------------------
# SalidaPaquete - Serializer completo para DETALLE (con reservas + pasajeros)
# ---------------------------------------------------------------------
class ReservaPasajeroDetalleSerializer(serializers.Serializer):
    """Serializer liviano para pasajero dentro del detalle de salida."""
    id = serializers.IntegerField()
    nombre = serializers.CharField(source="persona.nombre")
    apellido = serializers.CharField(source="persona.apellido")
    documento = serializers.CharField(source="persona.documento")
    tipo_documento = serializers.CharField(
        source="persona.tipo_documento.nombre", default=None
    )
    fecha_nacimiento = serializers.DateField(source="persona.fecha_nacimiento", default=None)
    es_titular = serializers.BooleanField()
    por_asignar = serializers.BooleanField()
    precio_asignado = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    monto_pagado = serializers.DecimalField(max_digits=12, decimal_places=2)
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=2)
    tiene_sena_pagada = serializers.BooleanField()
    esta_totalmente_pagado = serializers.BooleanField()
    ticket_numero = serializers.CharField(allow_null=True)
    voucher_codigo = serializers.CharField(allow_null=True)


class ReservaDetalleEnSalidaSerializer(serializers.Serializer):
    """Serializer para reserva dentro del detalle de salida, incluye pasajeros."""
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    estado = serializers.CharField()
    estado_display = serializers.CharField()
    cantidad_pasajeros = serializers.IntegerField(allow_null=True)
    fecha_reserva = serializers.DateTimeField()
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    monto_pagado = serializers.DecimalField(max_digits=12, decimal_places=2)
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=2)
    costo_total_estimado = serializers.DecimalField(max_digits=12, decimal_places=2)
    modalidad_facturacion = serializers.CharField(allow_null=True)
    condicion_pago = serializers.CharField(allow_null=True)
    observacion = serializers.CharField(allow_null=True)
    titular = serializers.SerializerMethodField()
    pasajeros = serializers.SerializerMethodField()

    def get_titular(self, obj):
        if not obj.titular:
            return None
        t = obj.titular
        return {
            "id": t.id,
            "nombre": t.nombre,
            "apellido": t.apellido,
            "documento": t.documento,
            "email": t.email,
            "telefono": t.telefono,
        }

    def get_pasajeros(self, obj):
        pasajeros = obj.pasajeros.select_related(
            "persona", "persona__tipo_documento"
        ).all()
        return ReservaPasajeroDetalleSerializer(pasajeros, many=True).data


class SalidaPaqueteDetalleSerializer(SalidaPaqueteSerializer):
    """
    Extiende SalidaPaqueteSerializer con el listado completo de reservas activas
    (con titular y pasajeros). Solo se usa en el endpoint de detalle (retrieve).
    """
    reservas = serializers.SerializerMethodField()

    class Meta(SalidaPaqueteSerializer.Meta):
        fields = SalidaPaqueteSerializer.Meta.fields + ["codigo", "reservas"]

    def get_reservas(self, obj):
        reservas_activas = obj.reservas.filter(activo=True).exclude(
            estado="cancelada"
        ).select_related(
            "titular", "habitacion", "habitacion__tipo_habitacion"
        ).prefetch_related(
            "pasajeros__persona__tipo_documento"
        ).order_by("fecha_reserva")
        return ReservaDetalleEnSalidaSerializer(reservas_activas, many=True).data


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
    
    # es el precio personalizado (el actual definido en PaqueteServicio.precio)
    precio = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    precio_base = serializers.SerializerMethodField()

    class Meta:
        model = PaqueteServicio
        fields = ["servicio_id", "nombre_servicio", "precio", "precio_base"]

    def get_precio_base(self, obj):
        """
        Devuelve el precio base del servicio asociado.
        Si no tiene precio, retorna 0.
        """
        if hasattr(obj.servicio, "precio") and obj.servicio.precio is not None:
            return obj.servicio.precio
        return Decimal("0")

    def validate_precio(self, value):
        if value in ("", None):
            return Decimal("0")
        return Decimal(value)


# ---------------------------------------------------------------------
# Paquete Serializer
# ---------------------------------------------------------------------
class PaqueteSerializer(serializers.ModelSerializer):
    # Código del paquete (generar si no existe en modelo)
    codigo = serializers.SerializerMethodField()
    
    tipo_paquete = TipoPaqueteSimpleSerializer(read_only=True)
    destino = DestinoNestedSerializer(read_only=True)
    distribuidora = DistribuidoraSimpleSerializer(read_only=True, allow_null=True)
    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)

    # Zona geográfica a nivel de paquete (lectura, derivada del destino)
    zona_geografica = serializers.SerializerMethodField(read_only=True)

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

    items_costo_default = ItemCostoPaqueteSerializer(
        many=True,
        read_only=True
    )

    items_costo_data = ItemCostoPaqueteSerializer(
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
    precio_venta_desde = serializers.SerializerMethodField()
    senia = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = Paquete
        fields = [
            "id",
            "codigo",
            "nombre",
            "tipo_paquete",
            "tipo_paquete_id",
            "destino",
            "destino_id",
            "zona_geografica",      # <-- agregado aquí (lectura)
            "distribuidora",
            "distribuidora_id",
            "moneda",
            "moneda_id",
            "servicios",
            "servicios_data",
            "items_costo_default",
            "items_costo_data",
            "modalidad",
            "precio",
            "precio_venta_desde",
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
    def _get_items_costo_from_initial(self):
        raw = getattr(self, "initial_data", {}).get("items_costo_data")
        if not raw:
            return []
        if isinstance(raw, str):
            try:
                data = json.loads(raw)
                return data if isinstance(data, list) else []
            except Exception:
                return []
        if isinstance(raw, list):
            return raw
        return []

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

        # Parsear servicios_data
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
                "servicio": servicio_id,
                "precio": Decimal(item.get("precio", 0) or 0)
            })
        data["servicios_data"] = servicios_cleaned

        # Parsear items_costo_data
        items_costo_raw = data.get("items_costo_data")
        items_costo_parsed = []
        if items_costo_raw:
            if isinstance(items_costo_raw, str):
                try:
                    parsed = json.loads(items_costo_raw)
                    if isinstance(parsed, list):
                        items_costo_parsed = parsed
                except Exception:
                    items_costo_parsed = []
            elif isinstance(items_costo_raw, list):
                items_costo_parsed = items_costo_raw
        data["items_costo_data"] = items_costo_parsed

        return super().to_internal_value(data)

    # ------------------
    # Validación condicional
    # ------------------
    def validate(self, attrs):
        # 🚩 Detectar si es un PATCH parcial sin servicios_data
        request = self.context.get("request")
        is_partial = request and request.method == "PATCH"

        # Si es PATCH y no se está enviando 'servicios_data', no validamos eso
        if is_partial and "servicios_data" not in self.initial_data:
            return super().validate(attrs)

        servicios = attrs.get("servicios_data") or self._get_servicios_from_initial()
        propio = attrs.get("propio", getattr(self.instance, "propio", False))

        if propio and not servicios:
            raise serializers.ValidationError({
                "servicios_data": "Para paquetes propios es obligatorio enviar al menos un servicio."
            })

        # Validar mínimo 2 ítems de costo para paquetes propios
        if propio and "items_costo_data" in self.initial_data:
            items_costo = attrs.get("items_costo_data") or self._get_items_costo_from_initial()
            if len(items_costo) < 2:
                raise serializers.ValidationError({
                    "items_costo_data": "Para paquetes propios se requieren al menos 2 ítems de costo."
                })

        # Validar que paquetes de distribuidora NO tengan cupos_habitaciones
        if not propio:
            salidas = self._get_salidas_from_initial()
            for salida_data in salidas:
                cupos_habitaciones = salida_data.get("cupos_habitaciones", [])
                if cupos_habitaciones:
                    raise serializers.ValidationError({
                        "salidas": "Los paquetes de distribuidora NO pueden tener cupos de habitación. Están sujetos a disponibilidad de la distribuidora."
                    })

        return super().validate(attrs)


    # --------- Campos calculados ---------
    def get_codigo(self, obj):
        """Generar código del paquete si no existe"""
        if hasattr(obj, 'codigo') and obj.codigo:
            return obj.codigo
        return f"PAQ-2024-{obj.id:04d}"
    
    def get_fecha_inicio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return salida.fecha_salida if salida else None

    def get_fecha_fin(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("-fecha_regreso").first()
        return salida.fecha_regreso if salida else None


    def get_precio(self, obj):
        """
        Devuelve el menor costo_base_desde de todas las salidas activas del paquete.

        costo_base_desde ya es el precio de catálogo completo (sin sumar servicios),
        tanto para propios como para distribuidoras.
        """
        salidas = obj.salidas.filter(activo=True)
        if not salidas.exists():
            return Decimal("0")

        precios_actual = [s.costo_base_desde for s in salidas if s.costo_base_desde is not None]
        return min(precios_actual) if precios_actual else Decimal("0")

    def get_precio_venta_desde(self, obj):
        """
        Retorna el menor precio_venta_sugerido_min de todas las salidas activas.
        Este campo ya incluye habitación + servicios + ganancia% para paquetes propios,
        o precio_catalogo + comision% para distribuidoras.
        No se suman servicios aquí para evitar doble conteo.
        """
        salidas = obj.salidas.filter(activo=True)
        if not salidas.exists():
            return Decimal("0")

        precios = [
            s.precio_venta_sugerido_min
            for s in salidas
            if s.precio_venta_sugerido_min is not None
        ]
        return min(precios) if precios else Decimal("0")

    def get_senia(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return getattr(salida, "senia", None)

    def get_imagen_url(self, obj):
        request = self.context.get("request")
        if obj.imagen and hasattr(obj.imagen, "url"):
            return request.build_absolute_uri(obj.imagen.url) if request else obj.imagen.url
        return None

    def get_zona_geografica(self, obj):
        """
        Zona geográfica del paquete (derivada del país del destino).
        Mismo formato que en DestinoNestedSerializer.
        """
        try:
            pais = obj.destino.ciudad.pais
            zona = getattr(pais, "zona_geografica", None)
            if not zona:
                return None
            return {
                "id": zona.id,
                "nombre": getattr(zona, "nombre", None),
                "descripcion": getattr(zona, "descripcion", None)
            }
        except Exception:
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

    def _recalcular_costo_base(self, salida, hoteles_ids, precios_catalogo_hoteles_data, precios_catalogo_habitaciones_data):
        """
        Valida cobertura de precios y recalcula costo_base_desde/hasta desde PrecioCatalogoHabitacion.
        Aplica tanto a paquetes propios como a distribuidoras — ambos usan el mismo catálogo.
        En UPDATE acepta precios previos en BD para hoteles no reenviados.
        """
        hoteles_en_salida = set(h.id if isinstance(h, Hotel) else h for h in hoteles_ids) if hoteles_ids else set()

        if hoteles_en_salida:
            hoteles_con_precio_hotel = set(
                obj.id
                for p in precios_catalogo_hoteles_data
                for obj in [self._resolve_fk_instance("hotel", p.get("hotel") or p.get("hotel_id"), Hotel)]
                if obj
            )
            hoteles_con_precio_habitacion = set()
            for precio_item in precios_catalogo_habitaciones_data:
                hab_obj = self._resolve_fk_instance(
                    "habitacion",
                    precio_item.get("habitacion") or precio_item.get("habitacion_id"),
                    Habitacion
                )
                if hab_obj and hab_obj.hotel_id in hoteles_en_salida:
                    hoteles_con_precio_habitacion.add(hab_obj.hotel_id)

            # Incluir precios previos en BD (para UPDATE donde no se re-envían todos)
            hoteles_con_precio_previo = set(
                PrecioCatalogoHotel.objects.filter(salida=salida).values_list('hotel_id', flat=True)
            ) | set(
                PrecioCatalogoHabitacion.objects.filter(
                    salida=salida,
                    habitacion__hotel_id__in=hoteles_en_salida
                ).values_list('habitacion__hotel_id', flat=True)
            )

            hoteles_con_precios = hoteles_con_precio_hotel | hoteles_con_precio_habitacion | hoteles_con_precio_previo
            hoteles_sin_precios = hoteles_en_salida - hoteles_con_precios

            if hoteles_sin_precios:
                nombres = []
                for hotel_id in hoteles_sin_precios:
                    try:
                        nombres.append(Hotel.objects.get(id=hotel_id).nombre)
                    except Hotel.DoesNotExist:
                        nombres.append(f"ID:{hotel_id}")
                raise serializers.ValidationError({
                    "precios_catalogo_habitaciones": f"Los siguientes hoteles no tienen precios de catálogo: {', '.join(nombres)}. Todos los hoteles deben tener precios (por hotel o por habitación)."
                })

        precios_habitacion_bd = salida.precios_catalogo_habitaciones.all()
        if precios_habitacion_bd.exists():
            precios_list = [pc.precio_catalogo for pc in precios_habitacion_bd]
            salida.costo_base_desde = min(precios_list)
            salida.costo_base_hasta = max(precios_list)
            salida.save(update_fields=["costo_base_desde", "costo_base_hasta"])

    def _sync_items_costo_paquete(self, paquete, items_costo_data):
        """Sincroniza ItemCostoPaquete: crea, actualiza y elimina los no enviados."""
        existentes = {icp.tipo_costo_id: icp for icp in paquete.items_costo_default.all()}
        enviados_ids = []

        for item in items_costo_data:
            # Soporta tanto objeto resuelto por serializer (tipo_costo) como raw (tipo_costo_id)
            tipo_costo_obj = item.get("tipo_costo")
            if not tipo_costo_obj:
                tipo_costo_id = item.get("tipo_costo_id")
                if not tipo_costo_id:
                    continue
                try:
                    tipo_costo_obj = TipoCostoSalida.objects.get(id=tipo_costo_id)
                except TipoCostoSalida.DoesNotExist:
                    continue
            monto = Decimal(str(item.get("monto", 0) or 0))

            if tipo_costo_obj.id in existentes:
                icp = existentes[tipo_costo_obj.id]
                if icp.monto != monto:
                    icp.monto = monto
                    icp.save()
            else:
                ItemCostoPaquete.objects.create(
                    paquete=paquete,
                    tipo_costo=tipo_costo_obj,
                    monto=monto
                )
            enviados_ids.append(tipo_costo_obj.id)

        if enviados_ids:
            paquete.items_costo_default.exclude(tipo_costo_id__in=enviados_ids).delete()
        else:
            paquete.items_costo_default.all().delete()

    def _sync_items_costo_salida(self, salida, items_costo_override_data):
        """
        Sincroniza ItemCostoSalida (overrides) para una salida específica.
        Si la lista está vacía → elimina todos los overrides.
        """
        existentes = {ics.tipo_costo_id: ics for ics in salida.items_costo.all()}
        enviados_ids = []

        for item in items_costo_override_data:
            tipo_costo_id = item.get("tipo_costo_id")
            if not tipo_costo_id:
                continue
            try:
                tipo_costo_obj = TipoCostoSalida.objects.get(id=tipo_costo_id, activo=True)
            except TipoCostoSalida.DoesNotExist:
                continue
            monto = Decimal(str(item.get("monto", 0) or 0))

            if tipo_costo_obj.id in existentes:
                ics = existentes[tipo_costo_obj.id]
                if ics.monto != monto:
                    ics.monto = monto
                    ics.save()
            else:
                ItemCostoSalida.objects.create(
                    salida=salida,
                    tipo_costo=tipo_costo_obj,
                    monto=monto
                )
            enviados_ids.append(tipo_costo_obj.id)

        salida.items_costo.exclude(tipo_costo_id__in=enviados_ids).delete()

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
        items_costo_data = validated_data.pop("items_costo_data", None)
        salidas_data = validated_data.pop("salidas", None)

        if servicios_data is None:
            servicios_data = self._get_servicios_from_initial() or []
        if items_costo_data is None:
            items_costo_data = self._get_items_costo_from_initial() or []
        if not salidas_data:
            salidas_data = self._get_salidas_from_initial() or []

        # 🧩 Resolver tipo_paquete (viene como tipo_paquete o tipo_paquete_id)
        tipo_paquete_val = validated_data.pop("tipo_paquete", None) or validated_data.pop("tipo_paquete_id", None)
        if tipo_paquete_val:
            tipo_paquete_obj = self._resolve_fk_instance("tipo_paquete", tipo_paquete_val, TipoPaquete)
            if tipo_paquete_obj:
                validated_data["tipo_paquete"] = tipo_paquete_obj

        paquete = Paquete.objects.create(**validated_data)

        # Crear ítems de costo por defecto del paquete
        if items_costo_data:
            self._sync_items_costo_paquete(paquete, items_costo_data)

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
            cupos_habitaciones_data = salida_data.pop("cupos_habitaciones", [])
            precios_catalogo_hoteles_data = salida_data.pop("precios_catalogo_hoteles", [])
            precios_catalogo_habitaciones_data = salida_data.pop("precios_catalogo_habitaciones", [])
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

            # Crear cupos de habitación SOLO para paquetes propios
            if paquete.propio:
                for cupo_item in cupos_habitaciones_data:
                    habitacion_obj = self._resolve_fk_instance("habitacion", cupo_item.get("habitacion") or cupo_item.get("habitacion_id"), Habitacion)
                    if habitacion_obj:
                        CupoHabitacionSalida.objects.create(
                            salida=salida,
                            habitacion=habitacion_obj,
                            cupo=cupo_item.get("cupo", 0)
                        )

            # Crear precios de catálogo por HOTEL (propios y distribuidoras)
            # Y automáticamente crear precios individuales para cada habitación del hotel
            for precio_item in precios_catalogo_hoteles_data:
                hotel_obj = self._resolve_fk_instance("hotel", precio_item.get("hotel") or precio_item.get("hotel_id"), Hotel)
                if hotel_obj:
                    precio_catalogo_hotel = Decimal(precio_item.get("precio_catalogo", 0) or 0)

                    # Guardar el precio genérico del hotel
                    PrecioCatalogoHotel.objects.create(
                        salida=salida,
                        hotel=hotel_obj,
                        precio_catalogo=precio_catalogo_hotel
                    )

                    # Crear automáticamente precios individuales para TODAS las habitaciones del hotel
                    habitaciones_hotel = Habitacion.objects.filter(hotel=hotel_obj, activo=True)
                    for habitacion in habitaciones_hotel:
                        # Solo crear si no existe ya un precio individual para esta habitación
                        # (permitir sobrescritura posterior)
                        PrecioCatalogoHabitacion.objects.get_or_create(
                            salida=salida,
                            habitacion=habitacion,
                            defaults={"precio_catalogo": precio_catalogo_hotel}
                        )

            # Crear precios de catálogo por HABITACIÓN (propios y distribuidoras)
            # Estos pueden sobrescribir los precios creados automáticamente por hotel
            for precio_item in precios_catalogo_habitaciones_data:
                habitacion_obj = self._resolve_fk_instance("habitacion", precio_item.get("habitacion") or precio_item.get("habitacion_id"), Habitacion)
                if habitacion_obj:
                    precio_catalogo_hab = Decimal(precio_item.get("precio_catalogo", 0) or 0)
                    # Usar update_or_create para sobrescribir si ya existe
                    PrecioCatalogoHabitacion.objects.update_or_create(
                        salida=salida,
                        habitacion=habitacion_obj,
                        defaults={"precio_catalogo": precio_catalogo_hab}
                    )

            # Recalcular costo_base_desde y costo_base_hasta desde precios de catálogo
            self._recalcular_costo_base(salida, hoteles_ids, precios_catalogo_hoteles_data, precios_catalogo_habitaciones_data)

            salida.calcular_precio_venta()
            HistorialPrecioPaquete.objects.create(
                salida=salida,
                precio=salida.costo_base_desde,
                vigente=True,
            )

        return paquete

    def update(self, instance, validated_data):
        import json

        servicios_data = validated_data.pop("servicios_data", None)
        items_costo_data = validated_data.pop("items_costo_data", None)
        salidas_data = validated_data.pop("salidas", None)

        # Si servicios_data viene como string (FormData) o ausencia en validated_data:
        if servicios_data is None:
            raw_servicios = getattr(self, "initial_data", {}).get("servicios_data")
            if isinstance(raw_servicios, str):
                try:
                    servicios_data = json.loads(raw_servicios)
                except Exception:
                    servicios_data = []
            elif isinstance(raw_servicios, list):
                servicios_data = raw_servicios
            else:
                servicios_data = []

        # Si salidas viene como string (FormData)
        if salidas_data is None:
            raw_salidas = getattr(self, "initial_data", {}).get("salidas")
            if isinstance(raw_salidas, str):
                try:
                    salidas_data = json.loads(raw_salidas)
                except Exception:
                    salidas_data = []
            elif isinstance(raw_salidas, list):
                salidas_data = raw_salidas
            else:
                salidas_data = []

        # Modalidad se mantiene (no se puede cambiar desde el front)
        modalidad_actual = instance.modalidad

        # --- Actualizar atributos base del paquete ---
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # --- Actualizar servicios ---
        # Normalizamos servicios_data: puede venir con 'servicio_id' o 'servicio'
        if servicios_data is not None:
            # Map de servicios actuales en DB: {servicio_id: PaqueteServicio obj}
            servicios_existentes = {ps.servicio.id: ps for ps in instance.paquete_servicios.all()}
            enviados_ids_servicios = []

            for item in servicios_data:
                # item puede ser {"servicio_id": 9, "precio": ""} ó {"servicio": 9, "precio": 10}
                servicio_val = item.get("servicio") or item.get("servicio_id")
                # Resolver instancia Servicio
                servicio_obj = self._resolve_fk_instance("servicio", servicio_val, Servicio)
                if not servicio_obj:
                    # omitir entradas inválidas
                    continue

                # Determinar precio (vacío => 0)
                precio_raw = item.get("precio", None)
                try:
                    precio_val = Decimal(precio_raw) if precio_raw not in (None, "") else Decimal("0")
                except Exception:
                    precio_val = Decimal("0")

                # Si ya existe, actualizar; si no, crear
                if servicio_obj.id in servicios_existentes:
                    ps_obj = servicios_existentes[servicio_obj.id]
                    if ps_obj.precio != precio_val:
                        ps_obj.precio = precio_val
                        ps_obj.save()
                else:
                    PaqueteServicio.objects.create(
                        paquete=instance,
                        servicio=servicio_obj,
                        precio=precio_val
                    )

                enviados_ids_servicios.append(servicio_obj.id)

            # Eliminar servicios que no fueron enviados (si se envió un listado)
            if enviados_ids_servicios:
                instance.paquete_servicios.exclude(servicio__id__in=enviados_ids_servicios).delete()
            else:
                # si enviaste un array vacío explícito → eliminar todos
                instance.paquete_servicios.all().delete()

            # Recalcular precios de venta de todas las salidas del paquete
            # (los precios vienen del catálogo; el recálculo actualiza precio_venta_sugerido)
            if instance.propio:
                for salida in instance.salidas.all():
                    salida.calcular_precio_venta()

        # --- Actualizar ítems de costo por defecto del paquete ---
        if items_costo_data is not None:
            self._sync_items_costo_paquete(instance, items_costo_data)
            # Recalcular precios de venta de todas las salidas
            if instance.propio:
                for salida in instance.salidas.all():
                    salida.calcular_precio_venta()

        # --- Actualizar salidas ---
        if salidas_data:
            # Obtener TODAS las salidas (activas e inactivas) para evitar duplicación
            salidas_existentes = {s.id: s for s in SalidaPaquete.objects.filter(paquete=instance)}
            enviados_ids = []

            for salida_data in salidas_data:
                salida_id = salida_data.get("id")
                hoteles_ids = salida_data.pop("hoteles", [])
                cupos_habitaciones_data = salida_data.pop("cupos_habitaciones", []) or []
                precios_catalogo_hoteles_data = salida_data.pop("precios_catalogo_hoteles", []) or []
                precios_catalogo_habitaciones_data = salida_data.pop("precios_catalogo_habitaciones", []) or []
                # Sentinel: None = no enviado (no tocar overrides), [] = borrar todos
                items_costo_override_data = salida_data.pop("items_costo_override_data", None)
                moneda_val = salida_data.pop("moneda", None) or salida_data.pop("moneda_id", None)
                temporada_val = salida_data.pop("temporada", None) or salida_data.pop("temporada_id", None)
                habitacion_fija_val = salida_data.pop("habitacion_fija", None) or salida_data.pop("habitacion_fija_id", None)

                moneda_obj = self._resolve_fk_instance("moneda", moneda_val, Moneda)
                temporada_obj = self._resolve_fk_instance("temporada", temporada_val, Temporada)
                habitacion_fija_obj = self._resolve_fk_instance("habitacion_fija", habitacion_fija_val, Habitacion)

                if not moneda_obj:
                    raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

                # Validación: paquetes de distribuidora NO deben tener cupos_habitaciones
                if not instance.propio and cupos_habitaciones_data:
                    raise serializers.ValidationError({
                        "salidas": "Los paquetes de distribuidora NO pueden tener cupos de habitación. Están sujetos a disponibilidad de la distribuidora."
                    })

                # Validación: si el paquete es fijo, solo puede tener 1 cupo_habitacion
                if modalidad_actual == Paquete.FIJO and len(cupos_habitaciones_data) > 1:
                    raise serializers.ValidationError({
                        "salidas": "Los paquetes en modalidad 'fijo' solo pueden tener un 'cupo_habitacion'."
                    })

                # Si la salida tiene ID, intentar actualizar; si no, buscar por fechas para evitar duplicados
                salida = None
                if salida_id and salida_id in salidas_existentes:
                    # Caso 1: Tiene ID y existe en BD
                    salida = salidas_existentes[salida_id]
                elif not salida_id:
                    # Caso 2: No tiene ID - buscar salida existente por fechas para evitar duplicación
                    fecha_salida = salida_data.get("fecha_salida")
                    fecha_regreso = salida_data.get("fecha_regreso")
                    if fecha_salida and fecha_regreso:
                        salida_existente = SalidaPaquete.objects.filter(
                            paquete=instance,
                            fecha_salida=fecha_salida,
                            fecha_regreso=fecha_regreso
                        ).first()
                        if salida_existente:
                            salida = salida_existente
                            salida_id = salida.id  # Asignar el ID para tracking

                if salida:
                    # ACTUALIZAR salida existente (reactivar si estaba inactiva)
                    salida.activo = True

                    # actualizar campos simples
                    for attr, value in salida_data.items():
                        setattr(salida, attr, value)

                    salida.moneda = moneda_obj
                    salida.temporada = temporada_obj
                    salida.habitacion_fija = habitacion_fija_obj
                    salida.save()

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

                    # --- Cupos habitaciones: SOLO para paquetes propios ---
                    if instance.propio:
                        enviados_habitaciones = []
                        for cupo_item in cupos_habitaciones_data:
                            habitacion_id = cupo_item.get("habitacion_id") or (cupo_item.get("habitacion", {}).get("id") if isinstance(cupo_item.get("habitacion"), dict) else None)
                            if not habitacion_id:
                                continue
                            habitacion_obj = self._resolve_fk_instance("habitacion", habitacion_id, Habitacion)
                            if not habitacion_obj:
                                continue

                            CupoHabitacionSalida.objects.update_or_create(
                                salida=salida,
                                habitacion=habitacion_obj,
                                defaults={"cupo": cupo_item.get("cupo", 0)}
                            )
                            enviados_habitaciones.append(habitacion_obj.id)

                        if cupos_habitaciones_data:
                            salida.cupos_habitaciones.exclude(habitacion__id__in=enviados_habitaciones).delete()

                    # --- Precios de catálogo por HOTEL: update_or_create y eliminación de los no enviados ---
                    # Y automáticamente crear/actualizar precios individuales para cada habitación del hotel
                    enviados_precios_hoteles = []
                    habitaciones_actualizadas_por_hotel = set()  # Track habitaciones actualizadas vía hotel

                    for precio_item in precios_catalogo_hoteles_data:
                        hotel_id = precio_item.get("hotel_id") or (precio_item.get("hotel", {}).get("id") if isinstance(precio_item.get("hotel"), dict) else None)
                        if not hotel_id:
                            continue
                        hotel_obj = self._resolve_fk_instance("hotel", hotel_id, Hotel)
                        if not hotel_obj:
                            continue

                        precio_catalogo_hotel = Decimal(precio_item.get("precio_catalogo", 0) or 0)

                        # Guardar el precio genérico del hotel
                        PrecioCatalogoHotel.objects.update_or_create(
                            salida=salida,
                            hotel=hotel_obj,
                            defaults={"precio_catalogo": precio_catalogo_hotel}
                        )
                        enviados_precios_hoteles.append(hotel_obj.id)

                        # Crear/actualizar automáticamente precios individuales para TODAS las habitaciones del hotel
                        habitaciones_hotel = Habitacion.objects.filter(hotel=hotel_obj, activo=True)
                        for habitacion in habitaciones_hotel:
                            # Actualizar o crear precio de habitación basado en el precio del hotel
                            PrecioCatalogoHabitacion.objects.update_or_create(
                                salida=salida,
                                habitacion=habitacion,
                                defaults={"precio_catalogo": precio_catalogo_hotel}
                            )
                            habitaciones_actualizadas_por_hotel.add(habitacion.id)

                    if precios_catalogo_hoteles_data:
                        # Obtener hoteles eliminados ANTES del delete (bug fix: antes se hacía después)
                        hoteles_eliminados = list(
                            salida.precios_catalogo_hoteles
                            .exclude(hotel__id__in=enviados_precios_hoteles)
                            .values_list('hotel_id', flat=True)
                        )

                        # Eliminar precios por hotel que ya no están en el payload
                        salida.precios_catalogo_hoteles.exclude(hotel__id__in=enviados_precios_hoteles).delete()

                        # Eliminar precios de habitaciones de hoteles removidos
                        if hoteles_eliminados:
                            habitaciones_a_eliminar = Habitacion.objects.filter(
                                hotel_id__in=hoteles_eliminados
                            ).values_list('id', flat=True)
                            PrecioCatalogoHabitacion.objects.filter(
                                salida=salida,
                                habitacion_id__in=habitaciones_a_eliminar
                            ).delete()

                    # --- Precios de catálogo por HABITACIÓN: update_or_create y eliminación de los no enviados ---
                    # Estos pueden sobrescribir los precios creados automáticamente por hotel
                    enviados_precios_habitaciones = []
                    for precio_item in precios_catalogo_habitaciones_data:
                        habitacion_id = precio_item.get("habitacion_id") or (precio_item.get("habitacion", {}).get("id") if isinstance(precio_item.get("habitacion"), dict) else None)
                        if not habitacion_id:
                            continue
                        habitacion_obj = self._resolve_fk_instance("habitacion", habitacion_id, Habitacion)
                        if not habitacion_obj:
                            continue

                        PrecioCatalogoHabitacion.objects.update_or_create(
                            salida=salida,
                            habitacion=habitacion_obj,
                            defaults={"precio_catalogo": Decimal(precio_item.get("precio_catalogo", 0) or 0)}
                        )
                        enviados_precios_habitaciones.append(habitacion_obj.id)

                    # Eliminar solo habitaciones de hoteles que fueron explícitamente incluidos en el payload.
                    # Hoteles no mencionados se dejan intactos para evitar pérdida de datos cuando
                    # el frontend envía datos parciales (ej: solo un hotel en modo 'hotel').
                    if precios_catalogo_habitaciones_data or precios_catalogo_hoteles_data:
                        habitaciones_a_mantener = set(enviados_precios_habitaciones) | habitaciones_actualizadas_por_hotel
                        # Hoteles explícitamente mencionados en el payload (hotel-mode o room-mode)
                        hoteles_en_payload = set(enviados_precios_hoteles)
                        if enviados_precios_habitaciones:
                            hoteles_en_payload |= set(
                                Habitacion.objects.filter(id__in=enviados_precios_habitaciones)
                                .values_list('hotel_id', flat=True)
                            )
                        # Solo eliminar habitaciones de hoteles presentes en el payload
                        salida.precios_catalogo_habitaciones.filter(
                            habitacion__hotel_id__in=hoteles_en_payload
                        ).exclude(habitacion__id__in=habitaciones_a_mantener).delete()

                    # Recalcular costo_base_desde y costo_base_hasta desde precios de catálogo
                    # Aplica tanto a propios como a distribuidoras
                    self._recalcular_costo_base(salida, hoteles_ids, precios_catalogo_hoteles_data, precios_catalogo_habitaciones_data)

                    # --- Ítems de costo override por salida ---
                    # None = no se envió → no tocar overrides existentes
                    # [] o lista = sincronizar
                    if items_costo_override_data is not None:
                        self._sync_items_costo_salida(salida, items_costo_override_data)

                    # Recalcular precios de venta después de actualizar precios
                    salida.calcular_precio_venta()

                    enviados_ids.append(salida_id)
                else:
                    # CREAR nueva salida (solo si no se encontró ninguna existente)
                    salida = SalidaPaquete.objects.create(
                        paquete=instance,
                        moneda=moneda_obj,
                        temporada=temporada_obj,
                        habitacion_fija=habitacion_fija_obj,
                        **{k: v for k, v in salida_data.items() if k not in ["hoteles"]}
                    )

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

                    # Crear cupos de habitación SOLO para paquetes propios
                    if instance.propio:
                        for cupo_item in cupos_habitaciones_data:
                            habitacion_id = cupo_item.get("habitacion_id") or (cupo_item.get("habitacion", {}).get("id") if isinstance(cupo_item.get("habitacion"), dict) else None)
                            if not habitacion_id:
                                continue
                            habitacion_obj = self._resolve_fk_instance("habitacion", habitacion_id, Habitacion)
                            if not habitacion_obj:
                                continue

                            CupoHabitacionSalida.objects.create(
                                salida=salida,
                                habitacion=habitacion_obj,
                                cupo=cupo_item.get("cupo", 0),
                            )

                    # Crear precios de catálogo por HOTEL (propios y distribuidoras)
                    # Y automáticamente crear precios individuales para cada habitación del hotel
                    for precio_item in precios_catalogo_hoteles_data:
                        hotel_id = precio_item.get("hotel_id") or (precio_item.get("hotel", {}).get("id") if isinstance(precio_item.get("hotel"), dict) else None)
                        if not hotel_id:
                            continue
                        hotel_obj = self._resolve_fk_instance("hotel", hotel_id, Hotel)
                        if not hotel_obj:
                            continue

                        precio_catalogo_hotel = Decimal(precio_item.get("precio_catalogo", 0) or 0)

                        # Guardar el precio genérico del hotel
                        PrecioCatalogoHotel.objects.create(
                            salida=salida,
                            hotel=hotel_obj,
                            precio_catalogo=precio_catalogo_hotel
                        )

                        # Crear automáticamente precios individuales para TODAS las habitaciones del hotel
                        habitaciones_hotel = Habitacion.objects.filter(hotel=hotel_obj, activo=True)
                        for habitacion in habitaciones_hotel:
                            # Solo crear si no existe ya un precio individual para esta habitación
                            PrecioCatalogoHabitacion.objects.get_or_create(
                                salida=salida,
                                habitacion=habitacion,
                                defaults={"precio_catalogo": precio_catalogo_hotel}
                            )

                    # Crear precios de catálogo por HABITACIÓN (propios y distribuidoras)
                    # Estos pueden sobrescribir los precios creados automáticamente por hotel
                    for precio_item in precios_catalogo_habitaciones_data:
                        habitacion_id = precio_item.get("habitacion_id") or (precio_item.get("habitacion", {}).get("id") if isinstance(precio_item.get("habitacion"), dict) else None)
                        if not habitacion_id:
                            continue
                        habitacion_obj = self._resolve_fk_instance("habitacion", habitacion_id, Habitacion)
                        if not habitacion_obj:
                            continue

                        precio_catalogo_hab = Decimal(precio_item.get("precio_catalogo", 0) or 0)
                        # Usar update_or_create para sobrescribir si ya existe
                        PrecioCatalogoHabitacion.objects.update_or_create(
                            salida=salida,
                            habitacion=habitacion_obj,
                            defaults={"precio_catalogo": precio_catalogo_hab}
                        )

                    # Recalcular costo_base_desde y costo_base_hasta desde precios de catálogo
                    self._recalcular_costo_base(salida, hoteles_ids, precios_catalogo_hoteles_data, precios_catalogo_habitaciones_data)

                    # Ítems de costo override para la nueva salida
                    if items_costo_override_data is not None:
                        self._sync_items_costo_salida(salida, items_costo_override_data)

                    salida.calcular_precio_venta()
                    HistorialPrecioPaquete.objects.create(
                        salida=salida,
                        precio=salida.costo_base_desde,
                        vigente=True,
                    )

                    enviados_ids.append(salida.id)

            # Desactivar salidas que no fueron enviadas (en lugar de eliminar)
            # No se eliminan porque pueden tener reservas asociadas con PROTECT
            for s_id, salida in salidas_existentes.items():
                if s_id not in enviados_ids:
                    salida.activo = False
                    salida.save(update_fields=['activo'])

        return instance
