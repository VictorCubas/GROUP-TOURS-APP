import django_filters
from .models import Hotel

class HotelFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')
    moneda = django_filters.CharFilter(field_name='moneda__nombre', lookup_expr='icontains')

    class Meta:
        model = Hotel
        fields = ['nombre', 'activo', 'moneda']
