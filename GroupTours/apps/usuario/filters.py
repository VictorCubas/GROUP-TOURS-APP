import django_filters
from django_filters.rest_framework import FilterSet
from django.db.models import Q
from .models import Usuario


class UsuarioFilter(FilterSet):
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains')
    empleado = django_filters.CharFilter(field_name='empleado__persona__documento', lookup_expr='icontains')
    rol = django_filters.CharFilter(method='filter_por_rol')
    activo = django_filters.BooleanFilter(field_name='activo')

    # 🔹 Filtro unificado para buscar por nombre, apellido, razón social, documento, teléfono o username
    busqueda = django_filters.CharFilter(method='filter_busqueda')

    class Meta:
        model = Usuario
        fields = ['username', 'empleado', 'rol', 'activo']

    def filter_busqueda(self, queryset, name, value):
        return queryset.filter(
            Q(username__icontains=value) |
            Q(empleado__persona__personafisica__nombre__icontains=value) |
            Q(empleado__persona__personafisica__apellido__icontains=value) |
            Q(empleado__persona__personajuridica__razon_social__icontains=value) |
            Q(empleado__persona__documento__icontains=value) |
            Q(empleado__persona__telefono__icontains=value)
        )

    def filter_por_rol(self, queryset, name, value):
        return queryset.filter(roles__nombre__icontains=value)
