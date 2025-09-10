from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import TipoPaqueteViewSet

urlpatterns = [
    path('', TipoPaqueteViewSet.as_view({'get':'list', 'post':'create'}), name='tipo-paquete'),
    path('<int:pk>/', TipoPaqueteViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='tipo-paquete-detail'),
    path('resumen/', TipoPaqueteViewSet.as_view({'get': 'resumen'}), name='tipo-paquete-resumen'),   
    path('todos/', TipoPaqueteViewSet.as_view({'get': 'todos'}), name='tipo-paquete-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
