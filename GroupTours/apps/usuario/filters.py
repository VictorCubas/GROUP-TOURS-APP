import django_filters
from django_filters.rest_framework import FilterSet
from django.db.models import Q
from .models import Usuario
from django.utils.timezone import make_aware
from datetime import datetime, timedelta


class UsuarioFilter(FilterSet):
    username = django_filters.CharFilter(field_name='username', lookup_expr='icontains')
    empleado = django_filters.CharFilter(field_name='empleado__persona__documento', lookup_expr='icontains')
    rol = django_filters.CharFilter(method='filter_por_rol')
    activo = django_filters.BooleanFilter(field_name='activo')

    # 🔹 Filtro unificado para buscar por nombre, apellido, razón social, documento, teléfono o username
    busqueda = django_filters.CharFilter(method='filter_busqueda')
    
    
    # 📅 Filtros de rango para fecha_ingreso
    fecha_registro_desde = django_filters.DateFilter(
        field_name='fecha_creacion',
        lookup_expr='gte'
    )
    fecha_registro_hasta = django_filters.DateFilter(
        field_name='fecha_creacion',
        lookup_expr='lte',
        method='filter_fecha_hasta'
    )
    
    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    class Meta:
        model = Usuario
        fields = ['username', 'empleado', 'rol', 'activo',
                  'fecha_registro_desde', 'fecha_registro_hasta',]

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
