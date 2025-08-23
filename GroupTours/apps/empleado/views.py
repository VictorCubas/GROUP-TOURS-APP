from rest_framework import viewsets
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from .models import Empleado
from .serializers import EmpleadoSerializer, EmpleadoCreateSerializer
from .filters import EmpleadoFilter

class EmpleadoPagination(PageNumberPagination):
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

class EmpleadoViewSet(viewsets.ModelViewSet):
    queryset = Empleado.objects.select_related('persona', 'puesto', 'tipo_remuneracion').order_by('-fecha_creacion')
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmpleadoFilter
    pagination_class = EmpleadoPagination
    permission_classes = []

    serializer_class = EmpleadoCreateSerializer

    def _serialize_empleado(self, obj):
        return EmpleadoSerializer(obj).data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            results = [self._serialize_empleado(obj) for obj in page]
            return self.get_paginated_response(results)
        results = [self._serialize_empleado(obj) for obj in queryset]
        return Response(results)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(self._serialize_empleado(obj))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self._serialize_empleado(instance))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(self._serialize_empleado(updated_instance))

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(self._serialize_empleado(updated_instance))
