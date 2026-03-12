import django_filters
from django.db.models import Q
from .models import Paquete, SalidaPaquete
from django.utils.timezone import make_aware
from datetime import datetime, timedelta


class PaqueteFilter(django_filters.FilterSet):
    # 🔹 Filtros directos
    tipo_paquete = django_filters.CharFilter(
        field_name="tipo_paquete__nombre",
        lookup_expr="icontains"
    )
    distribuidora = django_filters.CharFilter(
        field_name="distribuidora__nombre",
        lookup_expr="icontains"
    )
    destino = django_filters.CharFilter(
        field_name="destino__ciudad__nombre",
        lookup_expr="icontains"
    )
    propio = django_filters.BooleanFilter(field_name="propio")
    activo = django_filters.BooleanFilter(field_name="activo")

    # 🔹 Nuevo filtro de zona geográfica (igual que en Destino)
    zona_geografica = django_filters.CharFilter(
        field_name="destino__ciudad__pais__zona_geografica__nombre",
        lookup_expr="icontains",
        help_text="Filtrar por zona geográfica (ej: América del Sur, Europa, Caribe, etc.)"
    )

    # 🔹 Filtros adicionales
    modalidad = django_filters.CharFilter(
        field_name="modalidad",
        lookup_expr="iexact",  # búsqueda exacta pero insensible a mayúsculas
        help_text="Filtrar por modalidad (ej: fija, flexible)."
    )
    habitacion_fija = django_filters.BooleanFilter(
        field_name="habitacion_fija",
        help_text="Filtrar si el paquete tiene habitación fija."
    )

    # 🔹 Fechas
    fecha_creacion_desde = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="gte"
    )
    fecha_creacion_hasta = django_filters.DateFilter(
        field_name="fecha_creacion",
        lookup_expr="lte",
        method='filter_fecha_hasta'
    )

    def filter_fecha_hasta(self, queryset, name, value):
        siguiente_dia = datetime.combine(value, datetime.min.time()) + timedelta(days=1)
        siguiente_dia = make_aware(siguiente_dia)
        return queryset.filter(fecha_creacion__lt=siguiente_dia)

    # 🔹 Búsqueda unificada (nombre, destino, país o zona geográfica)
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = Paquete
        fields = [
            "tipo_paquete",
            "distribuidora",
            "destino",
            "propio",
            "activo",
            "zona_geografica",     # 🔹 agregado aquí
            "modalidad",
            "habitacion_fija",
            "fecha_creacion_desde",
            "fecha_creacion_hasta"
        ]

    def filter_busqueda(self, queryset, name, value):
        """
        Filtra paquetes por nombre, destino, país, zona geográfica o código.
        Busca por código en formato PAQ-2024-XXXX o solo el número.
        """
        # Intentar extraer el ID del código si viene en formato PAQ-2024-XXXX
        paquete_id = None
        if value.upper().startswith('PAQ-'):
            # Formato: PAQ-2024-0142 o PAQ-2024-142
            parts = value.split('-')
            if len(parts) >= 3:
                try:
                    paquete_id = int(parts[-1])  # Toma el último número
                except ValueError:
                    pass
        else:
            # Si es solo un número, intentar buscarlo como ID
            try:
                paquete_id = int(value)
            except ValueError:
                pass
        
        # Construir el query
        q_filters = Q(nombre__icontains=value) | \
                    Q(destino__ciudad__nombre__icontains=value) | \
                    Q(destino__ciudad__pais__nombre__icontains=value) | \
                    Q(destino__ciudad__pais__zona_geografica__nombre__icontains=value) | \
                    Q(tipo_paquete__nombre__icontains=value) | \
                    Q(distribuidora__nombre__icontains=value) | \
                    Q(modalidad__icontains=value)
        
        # Si detectamos un ID de paquete, agregarlo a la búsqueda
        if paquete_id is not None:
            q_filters |= Q(id=paquete_id)

        return queryset.filter(q_filters)


# ---------------------------------------------------------------------
# FILTRO DE SALIDAS DE PAQUETE
# ---------------------------------------------------------------------
class SalidaFilter(django_filters.FilterSet):
    # Filtros directos
    paquete_id = django_filters.NumberFilter(field_name="paquete_id")
    paquete = django_filters.CharFilter(
        field_name="paquete__nombre",
        lookup_expr="icontains",
        help_text="Filtrar por nombre del paquete"
    )
    activo = django_filters.BooleanFilter(field_name="activo")

    # Filtro por código de reserva (salidas que tienen esa reserva)
    reserva_codigo = django_filters.CharFilter(
        field_name="reservas__codigo",
        lookup_expr="icontains",
        help_text="Filtrar por código de reserva asociada"
    )

    # Rango de fechas de salida
    fecha_salida_desde = django_filters.DateFilter(
        field_name="fecha_salida",
        lookup_expr="gte",
        help_text="Fecha de salida desde (YYYY-MM-DD)"
    )
    fecha_salida_hasta = django_filters.DateFilter(
        field_name="fecha_salida",
        lookup_expr="lte",
        help_text="Fecha de salida hasta (YYYY-MM-DD)"
    )

    # Búsqueda unificada: nombre de paquete, código de salida o código de reserva
    busqueda = django_filters.CharFilter(method="filter_busqueda")

    class Meta:
        model = SalidaPaquete
        fields = [
            "paquete_id",
            "paquete",
            "activo",
            "reserva_codigo",
            "fecha_salida_desde",
            "fecha_salida_hasta",
            "busqueda",
        ]

    def filter_busqueda(self, queryset, name, value):
        """
        Busca por nombre del paquete, código de salida o código de reserva.
        """
        return queryset.filter(
            Q(paquete__nombre__icontains=value) |
            Q(codigo__icontains=value) |
            Q(reservas__codigo__icontains=value)
        ).distinct()
