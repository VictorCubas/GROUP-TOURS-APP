from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Paquete, SalidaPaquete
from .serializers import PaqueteSerializer, SalidaPaqueteSerializer, SalidaPaqueteActualizarFechasSerializer
from .filters import PaqueteFilter


# -------------------- PAGINACIÓN --------------------
class PaquetePagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"

    def get_paginated_response(self, data):
        return Response({
            "totalItems": self.page.paginator.count,
            "pageSize": self.get_page_size(self.request),
            "totalPages": self.page.paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": data,
        })


# -------------------- VIEWSET --------------------
class PaqueteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Paquete con soporte de:
    - Subida de imagen (MultiPartParser / FormData)
    - Filtrado por DjangoFilterBackend (incluye modalidad y habitacion_fija)
    - Paginación personalizada
    - Endpoints extra: resumen y todos
    """

    parser_classes = (MultiPartParser, FormParser, JSONParser)

    queryset = (
        Paquete.objects.select_related(
            "tipo_paquete",
            "destino",
            "destino__ciudad__pais__zona_geografica",  # ✅ acceso optimizado
            "distribuidora",
            "moneda"
        )
        .prefetch_related(
            "paquete_servicios__servicio",
            "salidas__moneda",
            "salidas__hoteles",
            "salidas__habitacion_fija__hotel",
        )
        .order_by("-fecha_creacion")
    )

    serializer_class = PaqueteSerializer
    pagination_class = PaquetePagination
    permission_classes = []
    filter_backends = [DjangoFilterBackend]
    filterset_class = PaqueteFilter

    # ----- ENDPOINT EXTRA: resumen -----
    @action(detail=False, methods=['get'], url_path='resumen')
    def resumen(self, request):
        total = Paquete.objects.count()
        activos = Paquete.objects.filter(activo=True).count()
        propios = Paquete.objects.filter(propio=True).count()
        de_distribuidora = Paquete.objects.filter(propio=False).count()

        data = [
            {"texto": "Total", "valor": str(total)},
            {"texto": "Activos", "valor": str(activos)},
            {"texto": "Propios", "valor": str(propios)},
            {"texto": "Distribuidora", "valor": str(de_distribuidora)},
        ]
        return Response(data)

    # ----- ENDPOINT EXTRA: todos -----
    @action(detail=False, methods=['get'], url_path='todos', pagination_class=None)
    def todos(self, request):
        queryset = (
            self.filter_queryset(
                self.get_queryset().filter(activo=True)
            )
            .values(
                "id",
                "nombre",
                "destino__ciudad__nombre",
                "destino__ciudad__pais__nombre",
                "destino__ciudad__pais__zona_geografica__nombre",  # ✅ nueva línea
            )
        )

        data = [
            {
                "id": item["id"],
                "nombre": item["nombre"],
                "destino": item["destino__ciudad__nombre"],
                "pais": item["destino__ciudad__pais__nombre"],
                "zona_geografica": item["destino__ciudad__pais__zona_geografica__nombre"],
            }
            for item in queryset
        ]
        return Response(data)


# -------------------- VIEWSET SALIDA PAQUETE --------------------
class SalidaPaqueteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las Salidas de Paquete.
    
    Endpoints disponibles:
    - GET /api/salidas/ - Listar todas las salidas
    - GET /api/salidas/{id}/ - Ver detalle de una salida
    - POST /api/salidas/ - Crear nueva salida (generalmente se hace desde el paquete)
    - PUT/PATCH /api/salidas/{id}/ - Actualizar salida completa
    - PATCH /api/salidas/{id}/actualizar_fechas/ - Actualizar solo fechas de salida
    - DELETE /api/salidas/{id}/ - Eliminar salida (soft delete con activo=False)
    """
    
    queryset = SalidaPaquete.objects.select_related(
        'paquete',
        'moneda',
        'temporada',
        'habitacion_fija'
    ).prefetch_related(
        'hoteles',
        'cupos_habitaciones',
        'precios_catalogo_hoteles',
        'precios_catalogo'
    ).order_by('-fecha_salida')
    
    serializer_class = SalidaPaqueteSerializer
    permission_classes = []
    
    def get_queryset(self):
        """
        Opcionalmente filtra por paquete_id si se proporciona en query params
        """
        queryset = super().get_queryset()
        paquete_id = self.request.query_params.get('paquete_id', None)
        
        if paquete_id:
            queryset = queryset.filter(paquete_id=paquete_id)
        
        return queryset
    
    @action(detail=True, methods=['patch'], url_path='actualizar-fechas')
    def actualizar_fechas(self, request, pk=None):
        """
        Endpoint específico para actualizar solo las fechas de una salida.
        
        Permite adelantar o retrasar fechas sin afectar otros campos.
        
        Ejemplo de uso:
        PATCH /api/salidas/123/actualizar-fechas/
        {
            "fecha_salida": "2025-12-06",
            "fecha_regreso": "2025-12-15"
        }
        
        Respuesta exitosa:
        {
            "id": 123,
            "fecha_salida": "2025-12-06",
            "fecha_regreso": "2025-12-15",
            "mensaje": "Fechas actualizadas correctamente"
        }
        """
        salida = self.get_object()
        
        # Usar el serializer especializado para actualizar fechas
        serializer = SalidaPaqueteActualizarFechasSerializer(
            salida, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Recalcular precios si es necesario (por si cambian las noches)
            salida.calcular_precio_venta()
            
            return Response({
                **serializer.data,
                "mensaje": "Fechas actualizadas correctamente",
                "paquete": salida.paquete.nombre
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete - marca la salida como inactiva en lugar de eliminarla
        """
        salida = self.get_object()
        salida.activo = False
        salida.save()
        
        return Response({
            "mensaje": "Salida desactivada correctamente",
            "id": salida.id
        }, status=status.HTTP_200_OK)
