from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

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
