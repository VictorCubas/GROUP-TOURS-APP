import django_filters
from .models import Destino

class DestinoFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')
    pais = django_filters.CharFilter(field_name='pais__nombre', lookup_expr='icontains')

    class Meta:
        model = Destino
        fields = ['nombre', 'activo', 'pais']
