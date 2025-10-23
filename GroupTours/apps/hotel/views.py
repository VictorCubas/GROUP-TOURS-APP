from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from apps.paquete.models import SalidaPaquete

from .models import CadenaHotelera, Hotel, Habitacion, Servicio
from .serializers import CadenaHoteleraSerializer, HotelSerializer, HabitacionSerializer, ServicioSimpleSerializer
from .filters import HotelFilter
from apps.servicio.filters import ServicioFilter

# -------------------- PAGINACIÓN --------------------
class HotelPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

# -------------------- CADENA HOTELERA --------------------
class CadenaHoteleraViewSet(viewsets.ModelViewSet):
    queryset = CadenaHotelera.objects.filter(activo=True)
    serializer_class = CadenaHoteleraSerializer
    permission_classes = []
    
    # Endpoint /cadenas/todos
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True))
        data = list(queryset.values('id', 'nombre'))
        return Response(data)

# -------------------- HABITACION --------------------
class HabitacionViewSet(viewsets.ModelViewSet):
    queryset = Habitacion.objects.select_related('hotel', 'moneda').prefetch_related('servicios')
    serializer_class = HabitacionSerializer
    permission_classes = []

# -------------------- HOTEL --------------------
class HotelViewSet(viewsets.ModelViewSet):
    queryset = (
        Hotel.objects
        .select_related("ciudad", "ciudad__pais", "cadena")
        .prefetch_related("habitaciones", "servicios")
        .order_by("-fecha_creacion")   # 👈 Orden descendente por fecha de creación
    )
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = HotelFilter

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total_hoteles = Hotel.objects.count()
        activos_hoteles = Hotel.objects.filter(activo=True).count()
        inactivos_hoteles = Hotel.objects.filter(activo=False).count()

        total_cadenas = CadenaHotelera.objects.count()

        return Response([
            {'texto': 'Total', 'valor': str(total_hoteles)},
            {'texto': 'Activos', 'valor': str(activos_hoteles)},
            {'texto': 'Inactivos', 'valor': str(inactivos_hoteles)},
            {'texto': 'Total Cadenas', 'valor': str(total_cadenas)},
        ])

    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True)).values(
            "id", "nombre",
            "ciudad__nombre", "ciudad__pais__nombre",
            "cadena__nombre"
        )
        hoteles = [
            {
                "id": h["id"],
                "nombre": h["nombre"],
                "ciudad": h["ciudad__nombre"],
                "pais": h["ciudad__pais__nombre"],
                "cadena": h["cadena__nombre"],
            }
            for h in queryset
        ]
        return Response(hoteles)
    
    
    @action(detail=False, methods=['get'], url_path='por-salida/(?P<salida_id>[^/.]+)', pagination_class=None)
    def por_salida(self, request, salida_id=None):
        """
        Devuelve los hoteles y habitaciones asociados a una salida de paquete.
        Incluye el cupo de cada habitación según CupoHabitacionSalida.
        Además, incluye un resumen ordenado de habitaciones por precio.
        """
        from decimal import Decimal
        from apps.paquete.models import CupoHabitacionSalida

        try:
            salida = SalidaPaquete.objects.select_related('paquete').prefetch_related(
                'paquete__paquete_servicios__servicio'
            ).get(pk=salida_id)
        except SalidaPaquete.DoesNotExist:
            return Response({"detail": "Salida no encontrada."}, status=404)

        # Hoteles asociados
        hoteles = salida.hoteles.prefetch_related(
            "habitaciones__servicios",
            "habitaciones__moneda",
            "servicios",
            "ciudad",
            "ciudad__pais",
            "cadena"
        )

        # Inyectar salida_id en el contexto del serializer para recuperar cupos y precios
        serializer = self.get_serializer(
            hoteles,
            many=True,
            context={'salida_id': salida_id, 'request': request}
        )

        # ========================================
        # RESUMEN ADICIONAL: Habitaciones ordenadas por precio
        # ========================================
        resumen_habitaciones = []

        # Calcular noches
        if salida.fecha_regreso and salida.fecha_salida:
            noches = (salida.fecha_regreso - salida.fecha_salida).days
        else:
            noches = 1

        # Calcular total de servicios del paquete SOLO si es paquete propio
        total_servicios = Decimal('0')
        if salida.paquete.propio:
            for ps in salida.paquete.paquete_servicios.all():
                if ps.precio and ps.precio > 0:
                    total_servicios += ps.precio
                elif hasattr(ps.servicio, 'precio') and ps.servicio.precio:
                    total_servicios += ps.servicio.precio

        # Factores de ganancia/comisión
        ganancia = salida.ganancia or Decimal('0')
        comision = salida.comision or Decimal('0')

        if salida.paquete.propio and ganancia > 0:
            factor = Decimal('1') + (ganancia / Decimal('100'))
        elif not salida.paquete.propio and comision > 0:
            factor = Decimal('1') + (comision / Decimal('100'))
        else:
            factor = Decimal('1')

        # Verificar si es paquete de distribuidora
        es_distribuidora = not salida.paquete.propio

        if es_distribuidora:
            # Para paquetes de distribuidora: usar precios de catálogo individuales por habitación
            from apps.paquete.models import PrecioCatalogoHabitacion

            # Obtener todos los precios de catálogo para esta salida
            precios_catalogo = {
                pc.habitacion_id: pc.precio_catalogo
                for pc in PrecioCatalogoHabitacion.objects.filter(salida_id=salida_id)
            }

            # Aunque no hay cupos, mostramos los hoteles asociados a la salida
            # para que el frontend tenga información sobre dónde se hospedan
            for hotel in hoteles:
                for habitacion in hotel.habitaciones.all():
                    # Obtener precio de catálogo específico para esta habitación
                    precio_catalogo = precios_catalogo.get(habitacion.id, Decimal('0'))
                    precio_venta_final = precio_catalogo * factor

                    resumen_habitaciones.append({
                        'habitacion_id': habitacion.id,
                        'hotel_id': hotel.id,
                        'hotel_nombre': hotel.nombre,
                        'habitacion_numero': habitacion.numero,
                        'habitacion_tipo': habitacion.tipo,
                        'capacidad': habitacion.capacidad,
                        'precio_noche': None,  # No aplica para distribuidora
                        'precio_catalogo': str(precio_catalogo),
                        'precio_venta_final': str(precio_venta_final),
                        'cupo': None,  # No se maneja cupo para distribuidora
                        'es_distribuidora': True
                    })

            # Ordenar por precio_venta_final (de menor a mayor)
            resumen_habitaciones_ordenado = sorted(
                resumen_habitaciones,
                key=lambda x: Decimal(x['precio_venta_final'])
            )

            # Identificar la más barata y la más cara
            habitacion_mas_barata = resumen_habitaciones_ordenado[0] if resumen_habitaciones_ordenado else None
            habitacion_mas_cara = resumen_habitaciones_ordenado[-1] if resumen_habitaciones_ordenado else None

        else:
            # Para paquetes propios: calcular normalmente
            for hotel in hoteles:
                for habitacion in hotel.habitaciones.all():
                    # Obtener cupo
                    try:
                        cupo_obj = CupoHabitacionSalida.objects.get(
                            salida_id=salida_id,
                            habitacion_id=habitacion.id
                        )
                        cupo = cupo_obj.cupo
                    except CupoHabitacionSalida.DoesNotExist:
                        cupo = 0

                    # Calcular precio
                    precio_noche = habitacion.precio_noche or Decimal('0')
                    precio_habitacion_total = precio_noche * noches
                    costo_base = precio_habitacion_total + total_servicios
                    precio_venta_final = costo_base * factor

                    resumen_habitaciones.append({
                        'habitacion_id': habitacion.id,
                        'hotel_id': hotel.id,
                        'hotel_nombre': hotel.nombre,
                        'habitacion_numero': habitacion.numero,
                        'habitacion_tipo': habitacion.tipo,
                        'capacidad': habitacion.capacidad,
                        'precio_noche': str(precio_noche),
                        'precio_venta_final': str(precio_venta_final),
                        'cupo': cupo,
                        'es_distribuidora': False
                    })

            # Ordenar por precio_venta_final (de menor a mayor)
            resumen_habitaciones_ordenado = sorted(
                resumen_habitaciones,
                key=lambda x: Decimal(x['precio_venta_final'])
            )

            # Identificar la más barata y la más cara
            habitacion_mas_barata = resumen_habitaciones_ordenado[0] if resumen_habitaciones_ordenado else None
            habitacion_mas_cara = resumen_habitaciones_ordenado[-1] if resumen_habitaciones_ordenado else None

        # ========================================
        # RESPUESTA CON ESTRUCTURA EXTENDIDA
        # ========================================
        return Response({
            'hoteles': serializer.data,  # Estructura original
            'es_distribuidora': es_distribuidora,
            'resumen_precios': {
                'noches': noches,
                'servicios_paquete_total': str(total_servicios) if salida.paquete.propio else None,
                'ganancia_porcentaje': str(ganancia) if salida.paquete.propio else None,
                'comision_porcentaje': str(comision) if not salida.paquete.propio else None,
                'factor_aplicado': str(factor),
                'habitacion_mas_barata': habitacion_mas_barata,
                'habitacion_mas_cara': habitacion_mas_cara,
                'habitaciones_ordenadas': resumen_habitaciones_ordenado,
                'precio_venta_sugerido_min': str(salida.precio_venta_sugerido_min) if salida.precio_venta_sugerido_min else None,
                'precio_venta_sugerido_max': str(salida.precio_venta_sugerido_max) if salida.precio_venta_sugerido_max else None,
            }
        })

# -------------------- SERVICIO --------------------
class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.order_by('-fecha_creacion').all()
    serializer_class = ServicioSimpleSerializer
    pagination_class = HotelPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServicioFilter

    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Servicio.objects.count()
        activos = Servicio.objects.filter(activo=True).count()
        inactivos = Servicio.objects.filter(activo=False).count()
        en_uso = Servicio.objects.filter(en_uso=True).count()
        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos,
            'total_en_uso': en_uso,
        })

    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        tipo = request.query_params.get('tipo')  # 'habitacion', 'hotel', 'paquete'
        queryset = self.filter_queryset(self.get_queryset().filter(activo=True))
        if tipo in ['habitacion', 'hotel', 'paquete']:
            queryset = queryset.filter(tipo=tipo)
        return Response(list(queryset.values('id', 'nombre', 'tipo')))
