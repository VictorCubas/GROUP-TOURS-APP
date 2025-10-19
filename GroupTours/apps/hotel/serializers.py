from .models import CadenaHotelera, Hotel, Habitacion, Servicio
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


class HabitacionSerializer(serializers.ModelSerializer):
    moneda_nombre = serializers.CharField(source='moneda.nombre', read_only=True)
    moneda_simbolo = serializers.CharField(source='moneda.simbolo', read_only=True)
    cupo = serializers.SerializerMethodField()

    # Campos adicionales para análisis de precios
    precio_calculado = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Habitacion
        fields = [
            'id', 'hotel', 'numero', 'tipo', 'capacidad',
            'precio_noche', 'moneda', 'moneda_nombre', 'moneda_simbolo', 'servicios',
            'cupo', 'precio_calculado', 'activo', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion', 'hotel']

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
        Incluye: habitación (por noches) + servicios del paquete + ganancia/comisión.
        Solo se calcula si hay salida_id en el contexto.
        """
        from decimal import Decimal
        from apps.paquete.models import SalidaPaquete

        salida_id = self.context.get('salida_id')
        if not salida_id:
            return None

        try:
            salida = SalidaPaquete.objects.select_related('paquete').prefetch_related(
                'paquete__paquete_servicios__servicio'
            ).get(pk=salida_id)
        except SalidaPaquete.DoesNotExist:
            return None

        # 1. Calcular precio por noche de esta habitación
        precio_noche = obj.precio_noche or Decimal('0')

        # 2. Calcular cantidad de noches
        if salida.fecha_regreso and salida.fecha_salida:
            noches = (salida.fecha_regreso - salida.fecha_salida).days
        else:
            noches = 1

        # 3. Precio base de la habitación por toda la estadía
        precio_habitacion_total = precio_noche * noches

        # 4. Sumar servicios incluidos en el paquete
        total_servicios = Decimal('0')
        for ps in salida.paquete.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, 'precio') and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        # 5. Calcular costo base total (habitación + servicios)
        costo_base_total = precio_habitacion_total + total_servicios

        # 6. Aplicar ganancia o comisión sobre el costo total
        ganancia = salida.ganancia or Decimal('0')
        comision = salida.comision or Decimal('0')

        if salida.paquete.propio and ganancia > 0:
            factor = Decimal('1') + (ganancia / Decimal('100'))
        elif not salida.paquete.propio and comision > 0:
            factor = Decimal('1') + (comision / Decimal('100'))
        else:
            factor = Decimal('1')

        # 7. Precio de venta final
        precio_venta_final = costo_base_total * factor

        return {
            'noches': noches,
            'precio_noche': str(precio_noche),
            'precio_habitacion_total': str(precio_habitacion_total),
            'servicios_paquete': str(total_servicios),
            'costo_base': str(costo_base_total),
            'ganancia_porcentaje': str(ganancia) if salida.paquete.propio else None,
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

        # Política: reemplaza habitaciones existentes
        instance.habitaciones.all().delete()
        for hab in habitaciones_data:
            servicios_hab = hab.pop('servicios', [])
            habitacion = Habitacion.objects.create(hotel=instance, **hab)
            habitacion.servicios.set(servicios_hab)

        return instance

    def validate_servicios(self, value):
        for servicio in value:
            if servicio.tipo != 'hotel':
                raise serializers.ValidationError(
                    f"El servicio '{servicio.nombre}' no es válido para Hoteles."
                )
        return value
