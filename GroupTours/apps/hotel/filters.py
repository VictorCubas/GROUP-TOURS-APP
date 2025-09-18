import django_filters
from django.db.models import Q
from .models import Hotel

class HotelFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')
    moneda = django_filters.CharFilter(field_name='moneda__nombre', lookup_expr='icontains')
    ciudad = django_filters.CharFilter(field_name='ciudad__nombre', lookup_expr='icontains')
    pais = django_filters.CharFilter(field_name='ciudad__pais__nombre', lookup_expr='icontains')
    cadena = django_filters.CharFilter(field_name='cadena__nombre', lookup_expr='icontains')
    buscar = django_filters.CharFilter(method='filter_buscar')

    class Meta:
        model = Hotel
        fields = ['nombre', 'activo', 'moneda', 'ciudad', 'pais', 'cadena', 'buscar']

    def filter_buscar(self, queryset, name, value):
        return queryset.filter(
            Q(ciudad__nombre__icontains=value) |
            Q(ciudad__pais__nombre__icontains=value) |
            Q(nombre__icontains=value)
        )
