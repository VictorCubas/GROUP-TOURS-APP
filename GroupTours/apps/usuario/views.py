from rest_framework import viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from .models import Usuario
from .serializers import UsuarioListadoSerializer, UsuarioCreateSerializer
from .filters import UsuarioFilter
from rest_framework.decorators import action
from django.utils import timezone
from datetime import timedelta

class UsuarioPagination(PageNumberPagination):
    page_size = 10
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


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = (
        Usuario.objects
        .select_related('empleado', 'empleado__persona')
        .prefetch_related('roles', 'roles__permisos')
        .order_by('-fecha_creacion')
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = UsuarioFilter
    pagination_class = UsuarioPagination
    permission_classes = []

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UsuarioListadoSerializer
        return UsuarioCreateSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(UsuarioListadoSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(UsuarioListadoSerializer(updated_instance).data)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(UsuarioListadoSerializer(updated_instance).data)

    @action(detail=False, methods=['get'], url_path='resumen', pagination_class=None)
    def resumen(self, request):
        total = Usuario.objects.count()
        activos = Usuario.objects.filter(activo=True).count()
        inactivos = Usuario.objects.filter(activo=False).count()
        
        ultimos_30_dias = timezone.now() - timedelta(days=30)
        nuevos = Usuario.objects.filter(fecha_creacion__gte=ultimos_30_dias).count()
        
        data = [
            {'texto': 'Total', 'valor': str(total)},
            {'texto': 'Activos', 'valor': str(activos)},
            {'texto': 'Inactivos', 'valor': str(inactivos)},
            {'texto': 'Nuevos últimos 30 días', 'valor': str(nuevos)},
        ]
        return Response(data)
