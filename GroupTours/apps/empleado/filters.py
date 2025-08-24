import django_filters
from django_filters.rest_framework import FilterSet
from django.db.models import Q
from .models import Empleado

class EmpleadoFilter(FilterSet):
    persona = django_filters.CharFilter(
        field_name='persona__documento',
        lookup_expr='icontains'
    )
    puesto = django_filters.CharFilter(
        field_name='puesto__nombre',
        lookup_expr='icontains'
    )
    activo = django_filters.BooleanFilter(
        field_name='activo'
    )

    # 📅 Filtros de rango para fecha_ingreso
    fecha_ingreso_desde = django_filters.DateFilter(
        field_name='fecha_ingreso',
        lookup_expr='gte'
    )
    fecha_ingreso_hasta = django_filters.DateFilter(
        field_name='fecha_ingreso',
        lookup_expr='lte'
    )
    
    # 🔹 Filtro unificado para buscar en nombre o apellido de personas físicas
    nombre_completo = django_filters.CharFilter(method='filter_nombre_completo')

    # 🔹 Filtro para personas jurídicas
    razon_social = django_filters.CharFilter(field_name='persona__personajuridica__razon_social', lookup_expr='icontains')
    
    documento = django_filters.CharFilter(field_name='persona__documento', lookup_expr='icontains')

    class Meta:
        model = Empleado
        fields = [
            'persona',
            'puesto',
            'activo',
            'fecha_ingreso_desde',
            'fecha_ingreso_hasta'
        ]

    def filter_nombre_completo(self, queryset, name, value):
        """
        Filtra empleados cuya persona física tenga nombre o apellido que contenga el valor.
        """
        return queryset.filter(
            Q(persona__personafisica__nombre__icontains=value) |
            Q(persona__personafisica__apellido__icontains=value)
        )
