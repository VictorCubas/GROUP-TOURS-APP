from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ReservaViewSet, ReservaServiciosAdicionalesViewSet

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

    # Endpoints globales de servicios adicionales
    path('servicios-adicionales/', ReservaServiciosAdicionalesViewSet.as_view({'get': 'list', 'post': 'create'}), name='servicios-adicionales'),
    path('servicios-adicionales/<int:pk>/', ReservaServiciosAdicionalesViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='servicios-adicionales-detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
