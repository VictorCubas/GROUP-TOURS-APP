# apps/facturacion/views.py
from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import (
    Empresa, Establecimiento, PuntoExpedicion,
    TipoImpuesto, Timbrado, FacturaElectronica
)
from .serializers import (
    EmpresaSerializer, EstablecimientoSerializer,
    PuntoExpedicionSerializer, TipoImpuestoSerializer,
    TimbradoSerializer, FacturaElectronicaSerializer
)

# ---------- ViewSets ----------
class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def empresa(self, request):
        empresa = Empresa.objects.first()
        if not empresa:
            return Response({"error": "No hay empresa registrada"}, status=404)
        return Response(self.serializer_class(empresa).data)

class EstablecimientoViewSet(viewsets.ModelViewSet):
    queryset = Establecimiento.objects.all()
    serializer_class = EstablecimientoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        establecimientos = self.get_queryset().filter(activo=True)
        return Response(self.serializer_class(establecimientos, many=True).data)

class PuntoExpedicionViewSet(viewsets.ModelViewSet):
    queryset = PuntoExpedicion.objects.all()
    serializer_class = PuntoExpedicionSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        puntos = self.get_queryset().filter(activo=True)
        return Response(self.serializer_class(puntos, many=True).data)

class TipoImpuestoViewSet(viewsets.ModelViewSet):
    queryset = TipoImpuesto.objects.all()
    serializer_class = TipoImpuestoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        tipos = self.get_queryset().filter(activo=True)
        return Response(self.serializer_class(tipos, many=True).data)

class TimbradoViewSet(viewsets.ModelViewSet):
    queryset = Timbrado.objects.all()
    serializer_class = TimbradoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        timbrados = self.get_queryset().filter(activo=True)
        return Response(self.serializer_class(timbrados, many=True).data)

# ---------- API Endpoints ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def guardar_configuracion_factura(request):
    empresa_data = request.data.get('empresa')
    factura_data = request.data.get('factura')

    if not factura_data:
        return Response({"error": "Los datos de factura son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

    # -------- Empresa Única --------
    empresa = Empresa.objects.first()
    if empresa_data:
        empresa_serializer = EmpresaSerializer(empresa, data=empresa_data, partial=True) if empresa else EmpresaSerializer(data=empresa_data)
        empresa_serializer.is_valid(raise_exception=True)
        empresa = empresa_serializer.save()

    # -------- Configuración de Factura --------
    factura_data['empresa'] = empresa.id
    factura_data['es_configuracion'] = True

    config_existente = FacturaElectronica.objects.filter(
        empresa=empresa,
        es_configuracion=True
    ).first()

    factura_serializer = FacturaElectronicaSerializer(config_existente, data=factura_data, partial=True) if config_existente else FacturaElectronicaSerializer(data=factura_data)
    factura_serializer.is_valid(raise_exception=True)
    factura_serializer.save()

    return Response({
        "empresa": EmpresaSerializer(empresa).data,
        "factura": factura_serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_configuracion_factura(request, empresa_id=None):
    """
    Retorna la configuración actual de facturación. Ignora el ID, ya que solo existe una empresa.
    """
    empresa = Empresa.objects.first()
    if not empresa:
        return Response({"error": "No existe empresa configurada"}, status=status.HTTP_404_NOT_FOUND)

    configuracion = FacturaElectronica.objects.filter(
        empresa=empresa,
        es_configuracion=True
    ).first()

    if not configuracion:
        return Response({"error": "No existe configuración de factura"}, status=status.HTTP_404_NOT_FOUND)

    return Response(FacturaElectronicaSerializer(configuracion).data, status=status.HTTP_200_OK)
