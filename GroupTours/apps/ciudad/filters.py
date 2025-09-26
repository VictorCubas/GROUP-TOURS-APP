# apps/ubicaciones/filters.py
import django_filters
from .models import Ciudad

class CiudadFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    pais = django_filters.NumberFilter(field_name='pais__id')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Ciudad
        fields = ['nombre', 'pais', 'activo']
