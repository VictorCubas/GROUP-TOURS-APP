import django_filters
from .models import Moneda

class MonedaFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    codigo = django_filters.CharFilter(field_name='codigo', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Moneda
        fields = ['nombre', 'codigo', 'activo']
