import django_filters
from django_filters.rest_framework import FilterSet
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
    
    # 🔹 Filtros por datos de persona
    documento = django_filters.CharFilter(field_name='persona__documento', lookup_expr='icontains')
    nombre = django_filters.CharFilter(field_name='persona__personafisica__nombre', lookup_expr='icontains')
    apellido = django_filters.CharFilter(field_name='persona__personafisica__apellido', lookup_expr='icontains')
    razon_social = django_filters.CharFilter(field_name='persona__personajuridica__razon_social', lookup_expr='icontains')

    class Meta:
        model = Empleado
        fields = [
            'persona',
            'puesto',
            'activo',
            'fecha_ingreso_desde',
            'fecha_ingreso_hasta'
        ]
