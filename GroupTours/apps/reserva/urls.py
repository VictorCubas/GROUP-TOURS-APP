from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ReservaViewSet, ReservaServiciosAdicionalesViewSet, PasajeroViewSet

# Importar views de comprobante para endpoints anidados
from apps.comprobante.views import ReservaComprobantesViewSet, ReservaVoucherViewSet

urlpatterns = [
    # Endpoints de Reserva
    path('', ReservaViewSet.as_view({'get': 'list', 'post': 'create'}), name='reserva'),
    path('<int:pk>/', ReservaViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='reserva-detail'),
    path('resumen/', ReservaViewSet.as_view({'get': 'resumen'}), name='reserva-resumen'),
    path('todos/', ReservaViewSet.as_view({'get': 'todos'}), name='reserva-todos'),

    # Endpoints de servicios adicionales por reserva
    path('<int:pk>/servicios-adicionales/', ReservaViewSet.as_view({'get': 'servicios_adicionales'}), name='reserva-servicios-adicionales'),
    path('<int:pk>/agregar-servicio/', ReservaViewSet.as_view({'post': 'agregar_servicio'}), name='reserva-agregar-servicio'),
    path('<int:pk>/resumen-costos/', ReservaViewSet.as_view({'get': 'resumen_costos'}), name='reserva-resumen-costos'),

    # Endpoints de pagos
    path('<int:pk>/registrar-senia/', ReservaViewSet.as_view({'post': 'registrar_senia'}), name='reserva-registrar-senia'),
    path('<int:pk>/registrar-pago/', ReservaViewSet.as_view({'post': 'registrar_pago'}), name='reserva-registrar-pago'),

    # Endpoints de comprobantes
    path('<int:pk>/generar-comprobante/', ReservaViewSet.as_view({'post': 'generar_comprobante'}), name='reserva-generar-comprobante'),
    path('<int:pk>/descargar-comprobante/', ReservaViewSet.as_view({'get': 'descargar_comprobante'}), name='reserva-descargar-comprobante'),

    # Endpoints de comprobantes y vouchers por reserva
    path('<int:reserva_pk>/comprobantes/', ReservaComprobantesViewSet.as_view({'get': 'list', 'post': 'create'}), name='reserva-comprobantes'),
    path('<int:reserva_pk>/comprobantes/<int:pk>/', ReservaComprobantesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='reserva-comprobante-detail'),
    path('<int:reserva_pk>/voucher/', ReservaVoucherViewSet.as_view({'get': 'list'}), name='reserva-voucher'),

    # Endpoints globales de servicios adicionales
    path('servicios-adicionales/', ReservaServiciosAdicionalesViewSet.as_view({'get': 'list', 'post': 'create'}), name='servicios-adicionales'),
    path('servicios-adicionales/<int:pk>/', ReservaServiciosAdicionalesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='servicios-adicionales-detail'),

    # Endpoints de Pasajeros
    path('pasajeros/', PasajeroViewSet.as_view({'get': 'list', 'post': 'create'}), name='pasajero-list'),
    path('pasajeros/<int:pk>/', PasajeroViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='pasajero-detail'),
    path('pasajeros/<int:pk>/estado-cuenta/', PasajeroViewSet.as_view({'get': 'estado_cuenta'}), name='pasajero-estado-cuenta'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
