from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Reserva
from .serializers import ReservaSerializer
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
