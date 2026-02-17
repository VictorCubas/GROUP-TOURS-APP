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
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_simbolo = serializers.CharField(source='moneda.simbolo', read_only=True)
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
            'precio_noche', 'moneda', 'moneda_nombre', 'moneda_simbolo', 'servicios',
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
        Calcula el precio de venta final de la habitación para una salida específica.

        Para PAQUETES PROPIOS:
        - Usa precio_noche de la habitación × cantidad de noches
        - Suma servicios del paquete
        - Aplica ganancia %

        Para PAQUETES DE DISTRIBUIDORA:
        - Usa precio_catalogo de PrecioCatalogoHabitacion (precio total, NO por noche)
        - NO suma servicios (ya están incluidos en el catálogo)
        - Aplica comisión %

        Solo se calcula si hay salida_id en el contexto.
        """
        from decimal import Decimal
        from apps.paquete.models import SalidaPaquete, PrecioCatalogoHabitacion

        salida_id = self.context.get('salida_id')
        if not salida_id:
            return None

        try:
            salida = SalidaPaquete.objects.select_related('paquete').prefetch_related(
                'paquete__paquete_servicios__servicio'
            ).get(pk=salida_id)
        except SalidaPaquete.DoesNotExist:
            return None

        # Calcular cantidad de noches
        if salida.fecha_regreso and salida.fecha_salida:
            noches = (salida.fecha_regreso - salida.fecha_salida).days
        else:
            noches = 1

        # === CASO 1: PAQUETE DE DISTRIBUIDORA ===
        if not salida.paquete.propio:
            # Intentar obtener el precio de catálogo para esta habitación
            try:
                precio_catalogo_obj = PrecioCatalogoHabitacion.objects.get(
                    salida_id=salida_id,
                    habitacion_id=obj.id
                )
                precio_base_habitacion = precio_catalogo_obj.precio_catalogo
                precio_origen = 'catalogo'
            except PrecioCatalogoHabitacion.DoesNotExist:
                # Fallback: usar precio_noche × noches si no hay precio de catálogo
                precio_noche = obj.precio_noche or Decimal('0')
                precio_base_habitacion = precio_noche * noches
                precio_origen = 'precio_noche_fallback'

            # Para distribuidoras, NO se suman servicios (ya incluidos en catálogo)
            total_servicios = Decimal('0')
            costo_base_total = precio_base_habitacion

            # Aplicar comisión
            comision = salida.comision or Decimal('0')
            if comision > 0:
                factor = Decimal('1') + (comision / Decimal('100'))
            else:
                factor = Decimal('1')

            precio_venta_final = costo_base_total * factor

            return {
                'noches': noches,
                'precio_catalogo': str(precio_base_habitacion),
                'precio_origen': precio_origen,
                'servicios_paquete': None,  # No aplica para distribuidoras
                'costo_base': str(costo_base_total),
                'ganancia_porcentaje': None,
                'comision_porcentaje': str(comision),
                'factor_aplicado': str(factor),
                'precio_venta_final': str(precio_venta_final)
            }

        # === CASO 2: PAQUETE PROPIO ===
        else:
            # 1. Calcular precio por noche de esta habitación
            precio_noche = obj.precio_noche or Decimal('0')

            # 2. Precio base de la habitación por toda la estadía (en su moneda original)
            precio_habitacion_total = precio_noche * noches

            # 3. Convertir precio de habitación a la moneda del paquete si es necesario
            if obj.moneda and salida.moneda and obj.moneda != salida.moneda:
                # Las monedas son diferentes, debemos convertir
                from apps.paquete.utils import convertir_entre_monedas
                from django.core.exceptions import ValidationError as DjangoValidationError
                
                try:
                    precio_habitacion_total_convertido = convertir_entre_monedas(
                        monto=precio_habitacion_total,
                        moneda_origen=obj.moneda,
                        moneda_destino=salida.moneda,
                        fecha=salida.fecha_salida
                    )
                    # Actualizar también precio_noche convertido para mostrar
                    precio_noche_convertido = precio_habitacion_total_convertido / noches if noches > 0 else Decimal('0')
                except DjangoValidationError:
                    # Si falla la conversión, usar el precio original (fallback)
                    precio_habitacion_total_convertido = precio_habitacion_total
                    precio_noche_convertido = precio_noche
            else:
                # Misma moneda o no hay moneda definida, usar directo
                precio_habitacion_total_convertido = precio_habitacion_total
                precio_noche_convertido = precio_noche

            # 4. Sumar servicios incluidos en el paquete
            total_servicios = Decimal('0')
            for ps in salida.paquete.paquete_servicios.all():
                if ps.precio and ps.precio > 0:
                    total_servicios += ps.precio
                elif hasattr(ps.servicio, 'precio') and ps.servicio.precio:
                    total_servicios += ps.servicio.precio

            # 5. Calcular costo base total (habitación convertida + servicios)
            costo_base_total = precio_habitacion_total_convertido + total_servicios

            # 6. Aplicar ganancia sobre el costo total
            ganancia = salida.ganancia or Decimal('0')
            if ganancia > 0:
                factor = Decimal('1') + (ganancia / Decimal('100'))
            else:
                factor = Decimal('1')

            # 7. Precio de venta final
            precio_venta_final = costo_base_total * factor

            return {
                'noches': noches,
                'precio_noche': str(precio_noche_convertido),
                'precio_habitacion_total': str(precio_habitacion_total_convertido),
                'servicios_paquete': str(total_servicios),
                'costo_base': str(costo_base_total),
                'ganancia_porcentaje': str(ganancia),
                'comision_porcentaje': None,
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
