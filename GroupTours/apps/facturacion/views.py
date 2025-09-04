# apps/facturacion/views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .models import (
    Empresa, Establecimiento, PuntoExpedicion,
    TipoImpuesto, Timbrado, FacturaElectronica
)
from .serializers import (
    EmpresaSerializer, EstablecimientoSerializer,
    PuntoExpedicionSerializer, TipoImpuestoSerializer,
    TimbradoSerializer, FacturaElectronicaSerializer
)


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        empresas = self.get_queryset()
        return Response(self.serializer_class(empresas, many=True).data)


class EstablecimientoViewSet(viewsets.ModelViewSet):
    queryset = Establecimiento.objects.all()
    serializer_class = EstablecimientoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        establecimientos = self.get_queryset()
        return Response(self.serializer_class(establecimientos, many=True).data)


class PuntoExpedicionViewSet(viewsets.ModelViewSet):
    queryset = PuntoExpedicion.objects.all()
    serializer_class = PuntoExpedicionSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        puntos = self.get_queryset()
        return Response(self.serializer_class(puntos, many=True).data)


class TipoImpuestoViewSet(viewsets.ModelViewSet):
    queryset = TipoImpuesto.objects.all()
    serializer_class = TipoImpuestoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        tipos = self.get_queryset()
        return Response(self.serializer_class(tipos, many=True).data)


class TimbradoViewSet(viewsets.ModelViewSet):
    queryset = Timbrado.objects.all()
    serializer_class = TimbradoSerializer
    permission_classes = []

    @action(detail=False, methods=['get'])
    def todos(self, request):
        timbrados = self.get_queryset()
        return Response(self.serializer_class(timbrados, many=True).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def guardar_configuracion_factura(request):
    empresa_data = request.data.get('empresa')
    factura_data = request.data.get('factura')

    if not factura_data:
        return Response({"error": "Los datos de factura son requeridos"}, status=status.HTTP_400_BAD_REQUEST)

    # -------- 1. Actualizar o crear empresa --------
    if empresa_data:
        empresa_id = empresa_data.get('id')
        if empresa_id:
            empresa = get_object_or_404(Empresa, id=empresa_id)
            empresa_serializer = EmpresaSerializer(empresa, data=empresa_data, partial=True)
        else:
            empresa_serializer = EmpresaSerializer(data=empresa_data)
        
        empresa_serializer.is_valid(raise_exception=True)
        empresa = empresa_serializer.save()
    else:
        # Si no se envía empresa, la buscamos en la factura
        empresa = get_object_or_404(Empresa, id=factura_data.get('empresa'))

    # -------- 2. Guardar configuración de factura --------
    factura_data['empresa'] = empresa.id
    factura_data['es_configuracion'] = True  # aseguramos que sea config

    # Si existe config previa para esta empresa, actualizar
    config_existente = FacturaElectronica.objects.filter(
        empresa=empresa,
        es_configuracion=True
    ).first()

    if config_existente:
        factura_serializer = FacturaElectronicaSerializer(config_existente, data=factura_data, partial=True)
    else:
        factura_serializer = FacturaElectronicaSerializer(data=factura_data)

    factura_serializer.is_valid(raise_exception=True)
    factura_serializer.save()

    return Response({
        "empresa": EmpresaSerializer(empresa).data,
        "factura": factura_serializer.data
    }, status=status.HTTP_200_OK)
    
    

@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_configuracion_factura(request, empresa_id):
    """
    Retorna la configuración actual de facturación para una empresa específica.
    """
    empresa = get_object_or_404(Empresa, id=empresa_id)

    configuracion = FacturaElectronica.objects.filter(
        empresa=empresa,
        es_configuracion=True
    ).first()

    if not configuracion:
        return Response(
            {"error": "No existe configuración para esta empresa"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response(
        FacturaElectronicaSerializer(configuracion).data,
        status=status.HTTP_200_OK
    )