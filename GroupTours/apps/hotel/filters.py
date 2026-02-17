import django_filters
from django.db.models import Q
from .models import Hotel, TipoHabitacion
from django.utils.timezone import make_aware
from datetime import datetime, timedelta

class HotelFilter(django_filters.FilterSet):
    # Filtros directos
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')
    ciudad = django_filters.CharFilter(field_name='ciudad__nombre', lookup_expr='icontains')
    pais = django_filters.CharFilter(field_name='ciudad__pais__nombre', lookup_expr='icontains')
    cadena = django_filters.CharFilter(field_name='cadena__nombre', lookup_expr='icontains')
    estrellas = django_filters.NumberFilter(field_name='estrellas', lookup_expr='exact')
    destino_id = django_filters.NumberFilter(field_name='destinos__id', lookup_expr='exact')

    # Filtro unificado
    busqueda = django_filters.CharFilter(method='filter_busqueda')

    # Fechas
    fecha_creacion_desde = django_filters.DateFilter(
        field_name='fecha_creacion',
        lookup_expr='gte'
    )
    fecha_creacion_hasta = django_filters.DateFilter(
        field_name='fecha_creacion',
        lookup_expr='lte',
        method='filter_fecha_hasta'
    )

    class Meta:
        model = Hotel
        fields = [
            'nombre', 'activo', 'ciudad', 
            'pais', 'cadena', 'busqueda',
            'fecha_creacion_desde', 'fecha_creacion_hasta',
            'estrellas', 'destino_id'
        ]

    def filter_fecha_hasta(self, queryset, name, value):
        """
        Incluye todo el día seleccionado para fecha_creacion_hasta.
        """
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    def filter_busqueda(self, queryset, name, value):
        """
        Filtra hoteles por nombre, ciudad o país.
        """
        return queryset.filter(
            Q(nombre__icontains=value) |
            Q(ciudad__nombre__icontains=value) |
            Q(ciudad__pais__nombre__icontains=value)
        )


class TipoHabitacionFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')
    busqueda = django_filters.CharFilter(method='filter_busqueda')

    class Meta:
        model = TipoHabitacion
        fields = ['nombre', 'activo', 'busqueda']

    def filter_busqueda(self, queryset, name, value):
        return queryset.filter(Q(nombre__icontains=value))
