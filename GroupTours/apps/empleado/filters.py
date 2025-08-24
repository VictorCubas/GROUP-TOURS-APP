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
    
    # 🔹 Filtro unificado para buscar en nombre, apellido o razón social
    busqueda = django_filters.CharFilter(method='filter_busqueda')

    # Filtro por documento individual (opcional si necesitas separar)
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

    def filter_busqueda(self, queryset, name, value):
        """
        Filtra empleados por:
        - persona física: nombre o apellido
        - persona jurídica: razón social
        """
        return queryset.filter(
            Q(persona__personafisica__nombre__icontains=value) |
            Q(persona__personafisica__apellido__icontains=value) |
            Q(persona__personajuridica__razon_social__icontains=value)
        )
