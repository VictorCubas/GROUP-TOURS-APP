# apps/facturacion/urls.py
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import (
    EmpresaViewSet, EstablecimientoViewSet,
    PuntoExpedicionViewSet, TipoImpuestoViewSet,
    TimbradoViewSet, guardar_configuracion_factura,
    obtener_configuracion_factura, generar_factura_reserva,
    obtener_factura_reserva, listar_facturas, obtener_factura_detalle,
    # Nuevos endpoints para facturación dual
    generar_factura_total, generar_factura_pasajero,
    generar_todas_facturas_pasajeros_view, facturas_reserva,
    facturas_pasajero, descargar_pdf_factura,
    # Endpoints para Notas de Crédito
    generar_nota_credito_total_view, generar_nota_credito_parcial_view,
    listar_notas_credito, detalle_nota_credito,
    notas_credito_de_factura, descargar_pdf_nota_credito
)

urlpatterns = [
    # Configuración
    path('empresa/', EmpresaViewSet.as_view({'get': 'empresa'}), name='empresa'),
    path('establecimientos/todos/', EstablecimientoViewSet.as_view({'get': 'todos'}), name='establecimientos-todos'),
    path('puntos-expedicion/todos/', PuntoExpedicionViewSet.as_view({'get': 'todos'}), name='puntos-expedicion-todos'),
    path('tipos-impuesto/todos/', TipoImpuestoViewSet.as_view({'get': 'todos'}), name='tipos-impuesto-todos'),
    path('timbrados/todos/', TimbradoViewSet.as_view({'get': 'todos'}), name='timbrados-todos'),
    path('guardar-config/', guardar_configuracion_factura, name='guardar-configuracion'),
    path('obtener-config/', obtener_configuracion_factura, name='obtener-configuracion'),

    # Generación y consulta de facturas (LEGACY - mantenido por compatibilidad)
    path('generar-factura/<int:reserva_id>/', generar_factura_reserva, name='generar-factura-reserva'),
    path('factura-reserva/<int:reserva_id>/', obtener_factura_reserva, name='obtener-factura-reserva'),
    path('facturas/', listar_facturas, name='listar-facturas'),
    path('facturas/<int:factura_id>/', obtener_factura_detalle, name='obtener-factura-detalle'),

    # Nuevos endpoints para facturación dual
    path('generar-factura-total/<int:reserva_id>/', generar_factura_total, name='generar-factura-total'),
    path('generar-factura-pasajero/<int:pasajero_id>/', generar_factura_pasajero, name='generar-factura-pasajero'),
    path('generar-todas-facturas-pasajeros/<int:reserva_id>/', generar_todas_facturas_pasajeros_view, name='generar-todas-facturas-pasajeros'),
    path('facturas-reserva/<int:reserva_id>/', facturas_reserva, name='facturas-reserva'),
    path('facturas-pasajero/<int:pasajero_id>/', facturas_pasajero, name='facturas-pasajero'),
    path('descargar-pdf/<int:factura_id>/', descargar_pdf_factura, name='descargar-pdf-factura'),

    # Endpoints para Notas de Crédito
    path('generar-nota-credito-total/<int:factura_id>/', generar_nota_credito_total_view, name='generar-nota-credito-total'),
    path('generar-nota-credito-parcial/<int:factura_id>/', generar_nota_credito_parcial_view, name='generar-nota-credito-parcial'),
    path('notas-credito/', listar_notas_credito, name='listar-notas-credito'),
    path('notas-credito/<int:nota_credito_id>/', detalle_nota_credito, name='detalle-nota-credito'),
    path('notas-credito-factura/<int:factura_id>/', notas_credito_de_factura, name='notas-credito-factura'),
    path('descargar-pdf-nota-credito/<int:nota_credito_id>/', descargar_pdf_nota_credito, name='descargar-pdf-nota-credito'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
