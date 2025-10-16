from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import Reserva, ReservaServiciosAdicionales
from .serializers import (
    ReservaSerializer,
    ReservaServiciosAdicionalesSerializer,
    ReservaServiciosAdicionalesCreateSerializer
)
from .filters import ReservaFilter

class ReservaPagination(PageNumberPagination):
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

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.select_related("titular", "paquete").prefetch_related("pasajeros").order_by('-fecha_reserva')
    serializer_class = ReservaSerializer
    pagination_class = ReservaPagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReservaFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Reserva.objects.count()
        pendientes = Reserva.objects.filter(estado="pendiente").count()
        confirmadas = Reserva.objects.filter(estado="confirmada").count()
        incompletas = Reserva.objects.filter(estado="incompleta").count()
        finalizadas = Reserva.objects.filter(estado="finalizada").count()
        canceladas = Reserva.objects.filter(estado="cancelada").count()

        data = [
            {"texto": "Total", "valor": total},
            {"texto": "Pendientes", "valor": pendientes},
            {"texto": "Confirmadas", "valor": confirmadas},
            {"texto": "Incompletas", "valor": incompletas},
            {"texto": "Finalizadas", "valor": finalizadas},
            {"texto": "Canceladas", "valor": canceladas},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = self.filter_queryset(
            self.get_queryset()
        ).values('id', 'titular__nombre', 'paquete__nombre')
        return Response(list(queryset))

    # ----- ENDPOINT: Listar servicios adicionales de una reserva -----
    @action(detail=True, methods=['get'], url_path='servicios-adicionales')
    def servicios_adicionales(self, request, pk=None):
        """
        GET /api/reservas/{id}/servicios-adicionales/
        Lista todos los servicios adicionales de una reserva específica
        """
        reserva = self.get_object()
        servicios = reserva.servicios_adicionales.filter(activo=True)
        serializer = ReservaServiciosAdicionalesSerializer(servicios, many=True)
        return Response(serializer.data)

    # ----- ENDPOINT: Agregar servicio adicional a una reserva -----
    @action(detail=True, methods=['post'], url_path='agregar-servicio')
    def agregar_servicio(self, request, pk=None):
        """
        POST /api/reservas/{id}/agregar-servicio/
        Body: {
            "servicio_id": 1,
            "cantidad": 2,
            "precio_unitario": 150.00,
            "observacion": "Solicitado por teléfono" (opcional)
        }
        """
        reserva = self.get_object()
        serializer = ReservaServiciosAdicionalesCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(reserva=reserva)
            # Retornar el servicio creado con toda la información
            response_serializer = ReservaServiciosAdicionalesSerializer(
                ReservaServiciosAdicionales.objects.get(id=serializer.instance.id)
            )
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ----- ENDPOINT: Obtener resumen de costos de una reserva -----
    @action(detail=True, methods=['get'], url_path='resumen-costos')
    def resumen_costos(self, request, pk=None):
        """
        GET /api/reservas/{id}/resumen-costos/
        Retorna un resumen de costos: base, adicionales y total
        """
        reserva = self.get_object()

        data = {
            "precio_base_paquete": reserva.precio_base_paquete,
            "cantidad_pasajeros": reserva.cantidad_pasajeros,
            "costo_paquete_total": reserva.precio_base_paquete * reserva.cantidad_pasajeros,
            "costo_servicios_adicionales": reserva.costo_servicios_adicionales,
            "costo_total_estimado": reserva.costo_total_estimado,
            "monto_pagado": reserva.monto_pagado,
            "saldo_pendiente": reserva.costo_total_estimado - reserva.monto_pagado,
        }
        return Response(data)


class ReservaServiciosAdicionalesViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios adicionales de forma global
    (no necesariamente vinculado a una reserva específica en la URL)
    """
    queryset = ReservaServiciosAdicionales.objects.select_related(
        'reserva', 'servicio'
    ).order_by('-fecha_agregado')
    serializer_class = ReservaServiciosAdicionalesSerializer
    permission_classes = []

    def get_queryset(self):
        """Permite filtrar por reserva usando query params"""
        queryset = super().get_queryset()
        reserva_id = self.request.query_params.get('reserva_id', None)
        if reserva_id is not None:
            queryset = queryset.filter(reserva_id=reserva_id)
        return queryset
