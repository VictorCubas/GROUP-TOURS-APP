import django_filters
from django_filters.rest_framework import FilterSet
from .models import Empleado

class EmpleadoFilter(FilterSet):
    persona = django_filters.CharFilter(field_name='persona__documento', lookup_expr='icontains')
    puesto = django_filters.CharFilter(field_name='puesto__nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Empleado
        fields = ['persona', 'puesto', 'activo']