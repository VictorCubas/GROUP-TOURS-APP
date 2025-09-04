# apps/facturacion/urls.py
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import (
    EmpresaViewSet, EstablecimientoViewSet,
    PuntoExpedicionViewSet, TipoImpuestoViewSet,
    TimbradoViewSet, guardar_configuracion_factura,
    obtener_configuracion_factura
)

urlpatterns = [
    path('empresas/todos/', EmpresaViewSet.as_view({'get': 'todos'}), name='empresas-todos'),
    path('establecimientos/todos/', EstablecimientoViewSet.as_view({'get': 'todos'}), name='establecimientos-todos'),
    path('puntos-expedicion/todos/', PuntoExpedicionViewSet.as_view({'get': 'todos'}), name='puntos-expedicion-todos'),
    path('tipos-impuesto/todos/', TipoImpuestoViewSet.as_view({'get': 'todos'}), name='tipos-impuesto-todos'),
    path('timbrados/todos/', TimbradoViewSet.as_view({'get': 'todos'}), name='timbrados-todos'),
    path('guardar-config/', guardar_configuracion_factura, name='guardar-configuracion'),
    path(
        'obtener-config/<int:empresa_id>/',
        obtener_configuracion_factura,
        name='obtener-configuracion'
    )

]

urlpatterns = format_suffix_patterns(urlpatterns)