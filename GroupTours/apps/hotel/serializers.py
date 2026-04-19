from .models import CadenaHotelera, Hotel, Habitacion, TipoHabitacion, Servicio
from rest_framework import serializers


class CadenaHoteleraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CadenaHotelera
        fields = "__all__"


class ServicioSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple para mostrar id y nombre del servicio."""
    class Meta:
        model = Servicio
        fields = ['id', 'nombre']


class TipoHabitacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoHabitacion
        fields = ['id', 'nombre', 'capacidad', 'activo', 'fecha_creacion', 'fecha_modificacion']
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


class HabitacionSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True, allow_null=True)
    moneda_simbolo = serializers.CharField(source='moneda.simbolo', read_only=True, allow_null=True)
    moneda_codigo = serializers.CharField(source='moneda.codigo', read_only=True, allow_null=True)
    tipo_habitacion_nombre = serializers.CharField(source='tipo_habitacion.nombre', read_only=True)
    capacidad = serializers.IntegerField(source='tipo_habitacion.capacidad', read_only=True)
    cupo = serializers.SerializerMethodField()
    id = serializers.IntegerField(required=False, allow_null=True)

    # Campos adicionales para análisis de precios
    precio_calculado = serializers.SerializerMethodField(read_only=True)
    
    # Permitir id opcional para actualizaciones (no obligatorio para creación)
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Habitacion
        fields = [
            'id', 'hotel', 'tipo_habitacion', 'tipo_habitacion_nombre', 'capacidad',
            'precio_noche', 'moneda', 'moneda_nombre', 'moneda_simbolo', 'moneda_codigo', 'servicios',
            'cupo', 'precio_calculado', 'activo', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'hotel']

    def get_cupo(self, obj):
        """
        Devuelve el cupo de la habitación para una salida específica.
        Si no hay contexto de salida_id, devuelve None.
        """
        salida_id = self.context.get('salida_id')
        if salida_id:
            from apps.paquete.models import CupoHabitacionSalida
            try:
                cupo_obj = CupoHabitacionSalida.objects.get(
                    salida_id=salida_id,
                    habitacion_id=obj.id
                )
                return cupo_obj.cupo
            except CupoHabitacionSalida.DoesNotExist:
                return 0
        return None

    def get_precio_calculado(self, obj):
        """
        Calcula el precio de venta de la habitación para una salida específica.

        Tanto propios como distribuidoras usan precio de catálogo:
        - PrecioCatalogoHabitacion (prioridad alta)
        - PrecioCatalogoHotel (fallback)

        Solo distribuidoras aplican comisión%. Propios no aplican ningún factor.
        Solo se calcula si hay salida_id en el contexto.

        ── LÓGICA ANTERIOR (cálculo automático para propios) ──────────────────────────
        Si en el futuro se quiere restaurar el cálculo automático para paquetes propios:

        if salida.paquete.propio:
            noches = (salida.fecha_regreso - salida.fecha_salida).days \
                     if salida.fecha_regreso and salida.fecha_salida else 1
            precio_noche = obj.precio_noche or Decimal('0')
            precio_habitacion_total = precio_noche * noches
            # Convertir a moneda de la salida si difieren:
            if obj.moneda and salida.moneda and obj.moneda != salida.moneda:
                from apps.paquete.utils import convertir_entre_monedas
                precio_habitacion_total = convertir_entre_monedas(
                    monto=precio_habitacion_total,
                    moneda_origen=obj.moneda,
                    moneda_destino=salida.moneda,
                    fecha=salida.fecha_salida
                )
            # Sumar servicios del paquete (PaqueteServicio.precio o Servicio.precio)
            total_servicios = Decimal('0')
            for ps in salida.paquete.paquete_servicios.all():
                if ps.precio and ps.precio > 0:
                    total_servicios += ps.precio
                elif hasattr(ps.servicio, 'precio') and ps.servicio.precio:
                    total_servicios += ps.servicio.precio
            # Aplicar ganancia%
            ganancia = salida.ganancia or Decimal('0')
            factor = Decimal('1') + (ganancia / Decimal('100')) if ganancia > 0 else Decimal('1')
            precio_venta_final = (precio_habitacion_total + total_servicios) * factor
            return {
                'noches': noches,
                'precio_noche': str(precio_noche),
                'precio_habitacion_total': str(precio_habitacion_total),
                'servicios_paquete': str(total_servicios),
                'ganancia_porcentaje': str(ganancia),
                'factor_aplicado': str(factor),
                'precio_venta_final': str(precio_venta_final),
            }
        ────────────────────────────────────────────────────────────────────────────────
        """
        from decimal import Decimal
        from apps.paquete.models import SalidaPaquete, PrecioCatalogoHabitacion, PrecioCatalogoHotel

        salida_id = self.context.get('salida_id')
        if not salida_id:
            return None

        try:
            salida = SalidaPaquete.objects.select_related('paquete').get(pk=salida_id)
        except SalidaPaquete.DoesNotExist:
            return None

        # Calcular cantidad de noches
        if salida.fecha_regreso and salida.fecha_salida:
            noches = (salida.fecha_regreso - salida.fecha_salida).days
        else:
            noches = 1

        # Buscar precio de catálogo por habitación (mayor prioridad)
        precio_catalogo_obj = PrecioCatalogoHabitacion.objects.filter(
            salida_id=salida_id,
            habitacion_id=obj.id
        ).first()

        if precio_catalogo_obj:
            precio_base = precio_catalogo_obj.precio_catalogo
            precio_origen = 'catalogo_habitacion'
        else:
            # Fallback al catálogo por hotel
            precio_hotel_obj = PrecioCatalogoHotel.objects.filter(
                salida_id=salida_id,
                hotel_id=obj.hotel_id
            ).first()
            if precio_hotel_obj:
                precio_base = precio_hotel_obj.precio_catalogo
                precio_origen = 'catalogo_hotel'
            else:
                return None

        # Solo distribuidoras aplican comisión
        comision = Decimal('0')
        if not salida.paquete.propio:
            comision = salida.comision or Decimal('0')

        factor = Decimal('1') + (comision / Decimal('100')) if comision > 0 else Decimal('1')
        precio_venta_final = precio_base * factor

        return {
            'noches': noches,
            'precio_catalogo': str(precio_base),
            'precio_origen': precio_origen,
            'comision_porcentaje': str(comision) if not salida.paquete.propio else None,
            'factor_aplicado': str(factor),
            'precio_venta_final': str(precio_venta_final)
        }

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'habitacion':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Habitaciones."
                )
        return value


class HotelSerializer(serializers.ModelSerializer):
    cadena_nombre = serializers.CharField(source='cadena.nombre', read_only=True)
    ciudad_nombre = serializers.CharField(source='ciudad.nombre', read_only=True)
    pais_id = serializers.IntegerField(source='ciudad.pais.id', read_only=True)
    pais_nombre = serializers.CharField(source='ciudad.pais.nombre', read_only=True)
    habitaciones = HabitacionSerializer(many=True)

    # Escritura: ids de los servicios del hotel
    servicios = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Servicio.objects.filter(tipo='hotel', activo=True)
    )
    # Lectura: id y nombre de cada servicio
    servicios_detalle = ServicioSimpleSerializer(
        many=True,
        source='servicios',
        read_only=True
    )

    class Meta:
        model = Hotel
        fields = [
            'id', 'nombre', 'descripcion', 'activo',
            'estrellas', 'direccion', 'ciudad', 'ciudad_nombre',
            'pais_id', 'pais_nombre', 'cadena', 'cadena_nombre',
            'servicios',          # ids para escritura
            'servicios_detalle',  # id y nombre para lectura
            'habitaciones',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']

    # ---- MÉTODOS PERSONALIZADOS ----
    def create(self, validated_data):
        habitaciones_data = validated_data.pop('habitaciones', [])
        servicios = validated_data.pop('servicios', [])
        hotel = Hotel.objects.create(**validated_data)
        hotel.servicios.set(servicios)
        for hab in habitaciones_data:
            servicios_hab = hab.pop('servicios', [])
            habitacion = Habitacion.objects.create(hotel=hotel, **hab)
            habitacion.servicios.set(servicios_hab)
        return hotel

    def update(self, instance, validated_data):
        habitaciones_data = validated_data.pop('habitaciones', [])
        servicios = validated_data.pop('servicios', [])

        # Actualiza campos simples del hotel
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Actualiza servicios ManyToMany
        instance.servicios.set(servicios)

        # === ACTUALIZACIÓN INTELIGENTE DE HABITACIONES ===
        # En lugar de eliminar y recrear, actualizamos/creamos/desactivamos según sea necesario
        habitaciones_existentes = {hab.id: hab for hab in instance.habitaciones.all()}
        habitaciones_en_payload = []

        # Procesar habitaciones del payload
        for hab_data in habitaciones_data:
            servicios_hab = hab_data.pop('servicios', [])
            hab_id = hab_data.pop('id', None)

            if hab_id and hab_id in habitaciones_existentes:
                # Actualizar habitación existente
                habitacion = habitaciones_existentes[hab_id]
                for attr, value in hab_data.items():
                    setattr(habitacion, attr, value)
                habitacion.save()
                habitacion.servicios.set(servicios_hab)
                habitaciones_en_payload.append(hab_id)
            else:
                # Crear nueva habitación
                habitacion = Habitacion.objects.create(hotel=instance, **hab_data)
                habitacion.servicios.set(servicios_hab)
                if habitacion.id:
                    habitaciones_en_payload.append(habitacion.id)

        # Manejar habitaciones que ya no están en el payload
        for hab_id, habitacion in habitaciones_existentes.items():
            if hab_id not in habitaciones_en_payload:
                # Verificar si tiene reservas asociadas
                if habitacion.reservas.filter(activo=True).exists():
                    # Soft delete: marcar como inactiva en lugar de eliminar
                    habitacion.activo = False
                    habitacion.save()
                else:
                    # Sin reservas: eliminar físicamente
                    try:
                        habitacion.delete()
                    except Exception:
                        # Si falla, hacer soft delete
                        habitacion.activo = False
                        habitacion.save()

        return instance

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'hotel':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Hoteles."
                )
        return value
