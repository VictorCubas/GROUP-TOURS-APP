from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Hotel
from .serializers import HotelSerializer
from .filters import HotelFilter

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

# -------------------- VIEWSET --------------------
class HotelViewSet(viewsets.ModelViewSet):
    queryset = Hotel.objects.select_related("moneda").order_by('-fecha_creacion')
    serializer_class = HotelSerializer
    pagination_class = HotelPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = HotelFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Hotel.objects.count()
        activos = Hotel.objects.filter(activo=True).count()
        inactivos = Hotel.objects.filter(activo=False).count()
        return Response({
            'total': total,
            'total_activos': activos,
            'total_inactivos': inactivos
        })

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = (
            self.filter_queryset(
                self.get_queryset()
                .filter(activo=True)
                .select_related("moneda")
            )
            .values(
                "id",
                "nombre",
                "precio_habitacion",
                "moneda__nombre",
                "moneda__codigo",
                "moneda__simbolo",
            )
        )

        # Transformar a la estructura deseada
        hoteles = [
            {
                "id": item["id"],
                "nombre": item["nombre"],
                "precio_habitacion": item["precio_habitacion"],
                "moneda": {
                    "nombre": item["moneda__nombre"],
                    "codigo": item["moneda__codigo"],
                    "simbolo": item["moneda__simbolo"],
                },
            }
            for item in queryset
        ]

        return Response(hoteles)

