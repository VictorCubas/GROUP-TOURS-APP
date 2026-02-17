from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import PaqueteViewSet, SalidaPaqueteViewSet

urlpatterns = [
    # Paquetes
    path('', PaqueteViewSet.as_view({'get': 'list', 'post': 'create'}), name='paquete'),
    path('<int:pk>/', PaqueteViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='paquete-detail'),
    path('resumen/', PaqueteViewSet.as_view({'get': 'resumen'}), name='paquete-resumen'),   
    path('todos/', PaqueteViewSet.as_view({'get': 'todos'}), name='paquete-todos'),
    
    # Salidas de Paquete
    path('salidas/', SalidaPaqueteViewSet.as_view({'get': 'list', 'post': 'create'}), name='salida-paquete-list'),
    path('salidas/<int:pk>/', SalidaPaqueteViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='salida-paquete-detail'),
    path('salidas/<int:pk>/actualizar-fechas/', SalidaPaqueteViewSet.as_view({'patch': 'actualizar_fechas'}), name='salida-paquete-actualizar-fechas'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
