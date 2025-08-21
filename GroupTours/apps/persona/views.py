from rest_framework import viewsets, serializers
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import FilterSet, DateFilter, DateFromToRangeFilter, DjangoFilterBackend
from rest_framework.decorators import action
import django_filters
from .models import Persona, PersonaFisica, PersonaJuridica
from .serializers import PersonaCreateSerializer, PersonaFisicaSerializer, PersonaJuridicaSerializer
from django.utils.timezone import make_aware
from datetime import datetime, timedelta
from django.db.models import Q
from django.db.models import F, ExpressionWrapper, fields
from django.utils.timezone import now

# --- Filtros ---
class PersonaFilter(FilterSet):
    documento = django_filters.CharFilter(field_name='documento', lookup_expr='icontains')
    telefono = django_filters.CharFilter(field_name='telefono', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    # --- Rango de fechas con filtros explícitos ---
    fecha_desde = DateFilter(field_name='fecha_creacion', lookup_expr='gte')  # mayor o igual
    fecha_hasta = DateFilter(field_name='fecha_creacion', method='filter_fecha_hasta')

    # --- Compatibilidad con filtros actuales ---
    fecha_creacion = DateFromToRangeFilter(field_name='fecha_creacion')  

    # Filtros específicos de PersonaFisica
    nombre = django_filters.CharFilter(field_name='personafisica__nombre', lookup_expr='icontains')
    apellido = django_filters.CharFilter(field_name='personafisica__apellido', lookup_expr='icontains')
    sexo = django_filters.CharFilter(field_name='personafisica__sexo', lookup_expr='exact')

    # Filtros específicos de PersonaJuridica
    razon_social = django_filters.CharFilter(field_name='personajuridica__razon_social', lookup_expr='icontains')
    
    # Filtro por tipo de persona
    tipo = django_filters.ChoiceFilter(
        choices=[('fisica', 'PersonaFisica'), ('juridica', 'PersonaJuridica')],
        method='filter_tipo'
    )

    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    def filter_tipo(self, queryset, name, value):
        if value == 'fisica':
            return queryset.filter(personafisica__id__isnull=False)
        elif value == 'juridica':
            return queryset.filter(personajuridica__id__isnull=False)
        return queryset


    class Meta:
        model = Persona
        fields = [
            'documento', 'telefono', 'activo',
            'fecha_creacion', 'fecha_desde', 'fecha_hasta',
            'nombre', 'apellido', 'sexo', 'razon_social'
        ]

# --- Paginación ---
class PersonaPagination(PageNumberPagination):
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
        
class PersonaPagination(PageNumberPagination):
    page_size = 5  # valor por defecto
    page_size_query_param = 'page_size'  # frontend puede pedir otra cantidad

    def get_paginated_response(self, data):
        return Response({
            'totalItems': self.page.paginator.count,
            'pageSize': self.get_page_size(self.request),
            'totalPages': self.page.paginator.num_pages,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })

# --- ViewSet ---
class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.select_related('tipo_documento').order_by('-fecha_creacion')
    filter_backends = [DjangoFilterBackend]
    filterset_class = PersonaFilter
    pagination_class = PersonaPagination
    permission_classes = []

    serializer_class = PersonaCreateSerializer

    def get_queryset(self):
        # Return a combined queryset or handle separately based on your needs
        return Persona.objects.select_related('tipo_documento').order_by('-fecha_creacion')
        # tipo = self.request.query_params.get('tipo')
        # if tipo == 'fisica':
        #     return PersonaFisica.objects.all()
        # elif tipo == 'juridica':
        #     return PersonaJuridica.objects.all()
        # return Persona.objects.all() # Usamos _serialize_persona para list y retrieve

    def _serialize_persona(self, obj):
        """Serializa según tipo concreto de persona y agrega el campo 'tipo'"""
        try:
            fisica = obj.personafisica
            data = PersonaFisicaSerializer(fisica).data
            return data
        except PersonaFisica.DoesNotExist:
            pass

        try:
            juridica = obj.personajuridica
            data = PersonaJuridicaSerializer(juridica).data
            return data
        except PersonaJuridica.DoesNotExist:
            pass

        return {}

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            results = [self._serialize_persona(obj) for obj in page]
            return self.get_paginated_response(results)

        results = [self._serialize_persona(obj) for obj in queryset]
        return Response(results)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        return Response(self._serialize_persona(obj))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        return Response(self._serialize_persona(instance))

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(self._serialize_persona(updated_instance))

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()
        return Response(self._serialize_persona(updated_instance))

    @action(detail=False, methods=['get'], url_path='resumen', pagination_class=None)
    def resumen(self, request):
        total = Persona.objects.count()
        activos = Persona.objects.filter(activo=True).count()
        inactivos = Persona.objects.filter(activo=False).count()

        # --- Calcular edad promedio de personas físicas ---
        personas_fisicas = PersonaFisica.objects.all()
        edades = [
            (now().date() - p.fecha_nacimiento).days // 365
            for p in personas_fisicas if p.fecha_nacimiento
        ]
        edad_promedio = round(sum(edades) / len(edades)) if edades else 0

        # --- Formatear respuesta como lista de objetos ---
        data = [
            {'texto': 'Total', 'valor': str(total)},
            {'texto': 'Activos', 'valor': str(activos)},
            {'texto': 'Inactivos', 'valor': str(inactivos)},
            {'texto': 'Edad Promedio', 'valor': str(edad_promedio)},
        ]

        return Response(data)