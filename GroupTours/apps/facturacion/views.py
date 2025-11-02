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
    TimbradoSerializer, FacturaElectronicaSerializer,
    FacturaElectronicaDetalladaSerializer
)
from .models import (
    generar_factura_desde_reserva,
    generar_factura_global,
    generar_factura_individual,
    generar_todas_facturas_pasajeros
)
from apps.reserva.models import Reserva, Pasajero
from django.core.exceptions import ValidationError as DjangoValidationError

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


@api_view(['POST'])
@permission_classes([AllowAny])
def generar_factura_reserva(request, reserva_id):
    """
    Genera una factura electrónica a partir de una reserva.

    Body (opcional):
        - subtipo_impuesto_id: ID del subtipo de impuesto a aplicar (si no se especifica, usa la configuración)
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id)

        subtipo_impuesto_id = request.data.get('subtipo_impuesto_id', None)

        # Generar la factura
        factura = generar_factura_desde_reserva(reserva, subtipo_impuesto_id)

        # Retornar la factura con todos los detalles
        serializer = FacturaElectronicaDetalladaSerializer(factura)

        return Response({
            "mensaje": "Factura generada exitosamente",
            "factura": serializer.data
        }, status=status.HTTP_201_CREATED)

    except DjangoValidationError as e:
        return Response({
            "error": str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": f"Error al generar factura: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_factura_reserva(request, reserva_id):
    """
    Obtiene la factura asociada a una reserva.
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id)

        factura = reserva.facturas.first()

        if not factura:
            return Response({
                "error": "Esta reserva no tiene factura generada"
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = FacturaElectronicaDetalladaSerializer(factura)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Error al obtener factura: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def listar_facturas(request):
    """
    Lista todas las facturas generadas (no incluye configuraciones).
    """
    facturas = FacturaElectronica.objects.filter(
        es_configuracion=False,
        activo=True
    ).order_by('-fecha_emision')

    serializer = FacturaElectronicaSerializer(facturas, many=True)

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_factura_detalle(request, factura_id):
    """
    Obtiene el detalle completo de una factura por su ID.
    """
    try:
        factura = get_object_or_404(FacturaElectronica, id=factura_id, es_configuracion=False)

        serializer = FacturaElectronicaDetalladaSerializer(factura)

        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Error al obtener factura: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ---------- Nuevos Endpoints para Facturación Dual ----------
@api_view(['POST'])
@permission_classes([AllowAny])
def generar_factura_total(request, reserva_id):
    """
    Genera una factura global para toda la reserva.

    POST /api/facturacion/generar-factura-total/{reserva_id}/

    Body (opcional):
        - subtipo_impuesto_id: ID del subtipo de impuesto a aplicar
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id, activo=True)
        subtipo_impuesto_id = request.data.get('subtipo_impuesto_id', None)

        # Generar la factura global
        factura = generar_factura_global(reserva, subtipo_impuesto_id)

        # Retornar la factura con todos los detalles
        serializer = FacturaElectronicaDetalladaSerializer(factura)

        return Response({
            "mensaje": "Factura global generada exitosamente",
            "factura": serializer.data
        }, status=status.HTTP_201_CREATED)

    except DjangoValidationError as e:
        return Response({
            "error": str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": f"Error al generar factura global: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def generar_factura_pasajero(request, pasajero_id):
    """
    Genera una factura individual para un pasajero específico.

    POST /api/facturacion/generar-factura-pasajero/{pasajero_id}/

    Body (opcional):
        - subtipo_impuesto_id: ID del subtipo de impuesto a aplicar
    """
    try:
        pasajero = get_object_or_404(Pasajero, id=pasajero_id)
        subtipo_impuesto_id = request.data.get('subtipo_impuesto_id', None)

        # Generar la factura individual
        factura = generar_factura_individual(pasajero, subtipo_impuesto_id)

        # Retornar la factura con todos los detalles
        serializer = FacturaElectronicaDetalladaSerializer(factura)

        return Response({
            "mensaje": "Factura individual generada exitosamente",
            "factura": serializer.data
        }, status=status.HTTP_201_CREATED)

    except DjangoValidationError as e:
        return Response({
            "error": str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": f"Error al generar factura individual: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def generar_todas_facturas_pasajeros_view(request, reserva_id):
    """
    Genera facturas individuales para todos los pasajeros que cumplan las condiciones.

    POST /api/facturacion/generar-todas-facturas-pasajeros/{reserva_id}/

    Body (opcional):
        - subtipo_impuesto_id: ID del subtipo de impuesto a aplicar
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id, activo=True)
        subtipo_impuesto_id = request.data.get('subtipo_impuesto_id', None)

        # Generar todas las facturas posibles
        resultado = generar_todas_facturas_pasajeros(reserva, subtipo_impuesto_id)

        mensaje = f"Se generaron {len(resultado['facturas_generadas'])} facturas exitosamente"
        if resultado['pasajeros_omitidos']:
            mensaje += f". {len(resultado['pasajeros_omitidos'])} pasajeros fueron omitidos"

        return Response({
            "mensaje": mensaje,
            "facturas_generadas": resultado['facturas_generadas'],
            "pasajeros_omitidos": resultado['pasajeros_omitidos']
        }, status=status.HTTP_201_CREATED)

    except DjangoValidationError as e:
        return Response({
            "error": str(e.message) if hasattr(e, 'message') else str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": f"Error al generar facturas: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def facturas_reserva(request, reserva_id):
    """
    Consulta todas las facturas de una reserva.

    GET /api/facturacion/facturas-reserva/{reserva_id}/
    """
    try:
        reserva = get_object_or_404(Reserva, id=reserva_id, activo=True)

        # Obtener factura global
        factura_total = reserva.facturas.filter(
            tipo_facturacion='total',
            activo=True
        ).first()

        # Obtener facturas individuales
        facturas_individuales = reserva.facturas.filter(
            tipo_facturacion='por_pasajero',
            activo=True
        ).order_by('fecha_emision')

        # Serializar
        factura_total_data = FacturaElectronicaSerializer(factura_total).data if factura_total else None
        facturas_individuales_data = FacturaElectronicaSerializer(facturas_individuales, many=True).data

        # Calcular resumen
        total_facturas = (1 if factura_total else 0) + facturas_individuales.count()
        monto_facturado = sum(
            f.total_general for f in [factura_total] + list(facturas_individuales) if f
        )
        pasajeros_sin_facturar = reserva.pasajeros.exclude(
            facturas__tipo_facturacion='por_pasajero',
            facturas__activo=True
        ).count() if reserva.modalidad_facturacion == 'individual' else 0

        return Response({
            "reserva": {
                "id": reserva.id,
                "codigo": reserva.codigo,
                "modalidad_facturacion": reserva.modalidad_facturacion
            },
            "factura_total": factura_total_data,
            "facturas_por_pasajero": facturas_individuales_data,
            "resumen": {
                "total_facturas": total_facturas,
                "monto_facturado": str(monto_facturado),
                "pasajeros_sin_facturar": pasajeros_sin_facturar
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Error al obtener facturas: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def facturas_pasajero(request, pasajero_id):
    """
    Consulta las facturas de un pasajero específico.

    GET /api/facturacion/facturas-pasajero/{pasajero_id}/
    """
    try:
        pasajero = get_object_or_404(Pasajero, id=pasajero_id)

        # Obtener facturas del pasajero
        facturas = pasajero.facturas.filter(activo=True).order_by('-fecha_emision')

        # Serializar
        facturas_data = FacturaElectronicaSerializer(facturas, many=True).data

        return Response({
            "pasajero": {
                "id": pasajero.id,
                "nombre": f"{pasajero.persona.nombre} {pasajero.persona.apellido}" if not pasajero.por_asignar else f"PENDIENTE_{pasajero.id}",
                "reserva_codigo": pasajero.reserva.codigo
            },
            "facturas": facturas_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": f"Error al obtener facturas: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def descargar_pdf_factura(request, factura_id):
    """
    Descarga el PDF de una factura.
    Si no existe, lo genera automáticamente.

    GET /api/facturacion/descargar-pdf/{factura_id}/

    Query params:
        - regenerar: true/false (default: false) - Fuerza la regeneración del PDF
    """
    from django.http import FileResponse
    import os

    try:
        factura = get_object_or_404(FacturaElectronica, id=factura_id, es_configuracion=False, activo=True)

        regenerar = request.query_params.get('regenerar', 'false').lower() == 'true'

        # Si no existe PDF o se solicita regenerar
        if not factura.pdf_generado or regenerar:
            try:
                print(f"Generando PDF para factura {factura.numero_factura}...")
                factura.generar_pdf()
                print(f"PDF generado exitosamente: {factura.pdf_generado.path}")

            except Exception as e:
                return Response({
                    "error": f"Error al generar PDF: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Verificar que el archivo físico existe
        if not factura.pdf_generado:
            return Response({
                "error": "No se pudo generar el PDF"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        pdf_path = factura.pdf_generado.path
        if not os.path.exists(pdf_path):
            return Response({
                "error": "El archivo PDF no existe en el sistema de archivos"
            }, status=status.HTTP_404_NOT_FOUND)

        # Retornar el archivo PDF
        try:
            response = FileResponse(
                open(pdf_path, 'rb'),
                content_type='application/pdf'
            )
            filename = f'factura_{factura.numero_factura}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({
                "error": f"Error al leer el archivo PDF: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Exception as e:
        return Response({
            "error": f"Error al descargar PDF: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
