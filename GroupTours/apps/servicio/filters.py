import django_filters
from .models import Servicio

class ServicioFilter(django_filters.FilterSet):
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    activo = django_filters.BooleanFilter(field_name='activo')

    class Meta:
        model = Servicio
        fields = ['nombre', 'activo']
