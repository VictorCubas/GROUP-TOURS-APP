from rest_framework import serializers
from .models import (
    CupoHabitacionSalida,
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
            "tipo": obj.habitacion.tipo,
            "hotel": obj.habitacion.hotel.nombre,
        }


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

    moneda = MonedaSimpleSerializer(read_only=True, allow_null=True)
    temporada = serializers.SerializerMethodField(read_only=True)

    cupos_habitaciones = CupoHabitacionSalidaSerializer(many=True, read_only=True)

    # Campos calculados para precio total (hotel + ganancia/comisión + servicios)
    precio_venta_total_min = serializers.SerializerMethodField(read_only=True)
    precio_venta_total_max = serializers.SerializerMethodField(read_only=True)


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
            "precio_venta_total_min",
            "precio_venta_total_max",
            "cupo",
            "senia",
            "activo",
            "hoteles",
            "hoteles_ids",
            "habitacion_fija",
            "habitacion_fija_id",
            "cupos_habitaciones",
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

    def get_precio_venta_total_min(self, obj):
        """
        Calcula el precio de venta total mínimo:
        precio_venta_sugerido_min + total de servicios del paquete
        """
        precio_venta_min = obj.precio_venta_sugerido_min or Decimal("0")

        # Calcular total de servicios del paquete
        total_servicios = Decimal("0")
        for ps in obj.paquete.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        return precio_venta_min + total_servicios

    def get_precio_venta_total_max(self, obj):
        """
        Calcula el precio de venta total máximo:
        precio_venta_sugerido_max + total de servicios del paquete
        """
        precio_venta_max = obj.precio_venta_sugerido_max or Decimal("0")

        # Calcular total de servicios del paquete
        total_servicios = Decimal("0")
        for ps in obj.paquete.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        return precio_venta_max + total_servicios


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

        return super().validate(attrs)


    # --------- Campos calculados ---------
    def get_fecha_inicio(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("fecha_salida").first()
        return salida.fecha_salida if salida else None

    def get_fecha_fin(self, obj):
        salida = obj.salidas.filter(activo=True).order_by("-fecha_regreso").first()
        return salida.fecha_regreso if salida else None


    def get_precio(self, obj):
        """
        Calcula dinámicamente el precio total del paquete:
        - Siempre busca el menor precio_actual y el mayor precio_final de las salidas activas.
        - Si el paquete es propio, suma también el total de los servicios.
        - Si no es propio, devuelve solo el menor precio_actual (sin sumar servicios).
        """

        total_servicios = Decimal("0")
        for ps in obj.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        salidas = obj.salidas.filter(activo=True)
        if not salidas.exists():
            return total_servicios if getattr(obj, "propio", False) else Decimal("0")

        precios_actual = [s.precio_actual for s in salidas if s.precio_actual is not None]
        precios_final = [s.precio_final for s in salidas if s.precio_final is not None]

        menor_precio_actual = min(precios_actual) if precios_actual else Decimal("0")
        mayor_precio_final = max(precios_final) if precios_final else Decimal("0")
        

        # ✅ Lógica: si es propio → suma servicios; si no → retorna solo menor_precio_actual
        if getattr(obj, "propio", False):
            return menor_precio_actual + total_servicios
        else:
            return menor_precio_actual

    def get_precio_venta_desde(self, obj):
        """
        Calcula el precio de venta mínimo para mostrar al cliente:
        Obtiene el menor precio_venta_total_min de todas las salidas activas.
        Este es el precio completo final (habitación + ganancia/comisión + servicios).
        """
        salidas = obj.salidas.filter(activo=True)
        if not salidas.exists():
            return Decimal("0")

        # Calcular total de servicios del paquete
        total_servicios = Decimal("0")
        for ps in obj.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        # Obtener todos los precio_venta_sugerido_min y sumarles los servicios
        precios_venta_totales = []
        for salida in salidas:
            if salida.precio_venta_sugerido_min:
                precio_total = salida.precio_venta_sugerido_min + total_servicios
                precios_venta_totales.append(precio_total)

        # Retornar el menor precio de venta total
        return min(precios_venta_totales) if precios_venta_totales else Decimal("0")

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
            
            
        # 🧩 Resolver tipo_paquete (viene como tipo_paquete o tipo_paquete_id)
        tipo_paquete_val = validated_data.pop("tipo_paquete", None) or validated_data.pop("tipo_paquete_id", None)
        if tipo_paquete_val:
            tipo_paquete_obj = self._resolve_fk_instance("tipo_paquete", tipo_paquete_val, TipoPaquete)
            if tipo_paquete_obj:
                validated_data["tipo_paquete"] = tipo_paquete_obj

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
            cupos_habitaciones_data = salida_data.pop("cupos_habitaciones", [])
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
                
                
            for cupo_item in cupos_habitaciones_data:
                habitacion_obj = self._resolve_fk_instance("habitacion", cupo_item.get("habitacion") or cupo_item.get("habitacion_id"), Habitacion)
                if habitacion_obj:
                    CupoHabitacionSalida.objects.create(
                        salida=salida,
                        habitacion=habitacion_obj,
                        cupo=cupo_item.get("cupo", 0)
                    )    
            

            salida.calcular_precio_venta()
            HistorialPrecioPaquete.objects.create(
                salida=salida,
                precio=salida.precio_actual,
                vigente=True,
            )

        return paquete

    def update(self, instance, validated_data):
        import json

        servicios_data = validated_data.pop("servicios_data", None)
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

        # --- Actualizar salidas ---
        if salidas_data:
            salidas_existentes = {s.id: s for s in instance.salidas.all()}
            enviados_ids = []

            for salida_data in salidas_data:
                salida_id = salida_data.get("id")
                hoteles_ids = salida_data.pop("hoteles", [])
                cupos_habitaciones_data = salida_data.pop("cupos_habitaciones", []) or []
                moneda_val = salida_data.pop("moneda", None) or salida_data.pop("moneda_id", None)
                temporada_val = salida_data.pop("temporada", None) or salida_data.pop("temporada_id", None)
                habitacion_fija_val = salida_data.pop("habitacion_fija", None) or salida_data.pop("habitacion_fija_id", None)

                moneda_obj = self._resolve_fk_instance("moneda", moneda_val, Moneda)
                temporada_obj = self._resolve_fk_instance("temporada", temporada_val, Temporada)
                habitacion_fija_obj = self._resolve_fk_instance("habitacion_fija", habitacion_fija_val, Habitacion)

                if not moneda_obj:
                    raise serializers.ValidationError({"salidas": "Cada salida debe incluir un 'moneda_id' válido."})

                # Validación: si el paquete es fijo, solo puede tener 1 cupo_habitacion
                if modalidad_actual == Paquete.FIJO and len(cupos_habitaciones_data) > 1:
                    raise serializers.ValidationError({
                        "salidas": "Los paquetes en modalidad 'fijo' solo pueden tener un 'cupo_habitacion'."
                    })

                if salida_id and salida_id in salidas_existentes:
                    salida = salidas_existentes[salida_id]
                    # actualizar campos simples
                    for attr, value in salida_data.items():
                        setattr(salida, attr, value)

                    salida.moneda = moneda_obj
                    salida.temporada = temporada_obj
                    salida.habitacion_fija = habitacion_fija_obj
                    salida.save()

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

                    # --- Cupos habitaciones: update_or_create y eliminación de los no enviados ---
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

                    enviados_ids.append(salida_id)
                else:
                    # crear nueva salida
                    salida = SalidaPaquete.objects.create(
                        paquete=instance,
                        moneda=moneda_obj,
                        temporada=temporada_obj,
                        habitacion_fija=habitacion_fija_obj,
                        **{k: v for k, v in salida_data.items() if k not in ["hoteles"]}
                    )

                    if hoteles_ids:
                        salida.hoteles.set(hoteles_ids)

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

                    salida.calcular_precio_venta()
                    HistorialPrecioPaquete.objects.create(
                        salida=salida,
                        precio=salida.precio_actual,
                        vigente=True,
                    )

                    enviados_ids.append(salida.id)

            # Eliminar salidas que no fueron enviadas
            for s_id, salida in salidas_existentes.items():
                if s_id not in enviados_ids:
                    salida.delete()

        return instance
