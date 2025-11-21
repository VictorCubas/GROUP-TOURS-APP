# apps/facturacion/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmpresaViewSet, EstablecimientoViewSet,
    PuntoExpedicionViewSet, TipoImpuestoViewSet,
    TimbradoViewSet, guardar_configuracion_factura,
    obtener_configuracion_factura, generar_factura_reserva,
    obtener_factura_reserva, obtener_factura_detalle,
    # Nuevos ViewSets con filtros y paginación
    FacturaElectronicaViewSet, NotaCreditoElectronicaViewSet,
    # Endpoints para facturación dual
    generar_factura_total, generar_factura_pasajero,
    generar_todas_facturas_pasajeros_view, facturas_reserva,
    facturas_pasajero,
    # Endpoints para Notas de Crédito
    generar_nota_credito_total_view, generar_nota_credito_parcial_view,
    notas_credito_de_factura,
    # Endpoints para descargar PDFs
    descargar_pdf_factura, descargar_pdf_nota_credito
)

# Router para los ViewSets con filtros y paginación
router = DefaultRouter()
router.register(r'facturas', FacturaElectronicaViewSet, basename='factura')
router.register(r'notas-credito', NotaCreditoElectronicaViewSet, basename='nota-credito')

urlpatterns = [
    # ========================================
    # CONFIGURACIÓN
    # ========================================
    path('empresa/', EmpresaViewSet.as_view({'get': 'empresa'}), name='empresa'),
    path('establecimientos/todos/', EstablecimientoViewSet.as_view({'get': 'todos'}), name='establecimientos-todos'),
    path('puntos-expedicion/todos/', PuntoExpedicionViewSet.as_view({'get': 'todos'}), name='puntos-expedicion-todos'),
    path('tipos-impuesto/todos/', TipoImpuestoViewSet.as_view({'get': 'todos'}), name='tipos-impuesto-todos'),
    path('timbrados/todos/', TimbradoViewSet.as_view({'get': 'todos'}), name='timbrados-todos'),
    path('guardar-config/', guardar_configuracion_factura, name='guardar-configuracion'),
    path('obtener-config/', obtener_configuracion_factura, name='obtener-configuracion'),

    # ========================================
    # GENERACIÓN DE FACTURAS
    # ========================================
    # LEGACY - mantenido por compatibilidad
    path('generar-factura/<int:reserva_id>/', generar_factura_reserva, name='generar-factura-reserva'),
    path('factura-reserva/<int:reserva_id>/', obtener_factura_reserva, name='obtener-factura-reserva'),
    path('factura-detalle/<int:factura_id>/', obtener_factura_detalle, name='obtener-factura-detalle'),

    # Facturación dual
    path('generar-factura-total/<int:reserva_id>/', generar_factura_total, name='generar-factura-total'),
    path('generar-factura-pasajero/<int:pasajero_id>/', generar_factura_pasajero, name='generar-factura-pasajero'),
    path('generar-todas-facturas-pasajeros/<int:reserva_id>/', generar_todas_facturas_pasajeros_view, name='generar-todas-facturas-pasajeros'),

    # Consultas de facturas por reserva/pasajero
    path('facturas-reserva/<int:reserva_id>/', facturas_reserva, name='facturas-reserva'),
    path('facturas-pasajero/<int:pasajero_id>/', facturas_pasajero, name='facturas-pasajero'),

    # ========================================
    # GENERACIÓN DE NOTAS DE CRÉDITO
    # ========================================
    path('generar-nota-credito-total/<int:factura_id>/', generar_nota_credito_total_view, name='generar-nota-credito-total'),
    path('generar-nota-credito-parcial/<int:factura_id>/', generar_nota_credito_parcial_view, name='generar-nota-credito-parcial'),

    # Consultas de notas de crédito
    path('notas-credito-factura/<int:factura_id>/', notas_credito_de_factura, name='notas-credito-factura'),

    # ========================================
    # DESCARGA DE PDFs
    # ========================================
    path('descargar-pdf/<int:factura_id>/', descargar_pdf_factura, name='descargar-pdf-factura'),
    path('descargar-pdf-nota-credito/<int:nota_credito_id>/', descargar_pdf_nota_credito, name='descargar-pdf-nota-credito'),

    # ========================================
    # VIEWSETS CON FILTROS Y PAGINACIÓN
    # ========================================
    # Incluye las rutas del router para:
    # - GET /api/facturacion/facturas/ (list con filtros y paginación)
    # - GET /api/facturacion/facturas/{id}/ (retrieve detallado)
    # - GET /api/facturacion/facturas/resumen/ (resumen general)
    # - GET /api/facturacion/facturas/{id}/descargar-pdf/ (descargar PDF)
    # - POST /api/facturacion/facturas/{id}/anular/ (anular factura)
    # - GET /api/facturacion/notas-credito/ (list con filtros y paginación)
    # - GET /api/facturacion/notas-credito/{id}/ (retrieve detallado)
    # - GET /api/facturacion/notas-credito/resumen/ (resumen general)
    # - GET /api/facturacion/notas-credito/{id}/descargar-pdf/ (descargar PDF)
    path('', include(router.urls)),
]
