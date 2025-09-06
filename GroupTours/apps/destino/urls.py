from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import DestinoViewSet

urlpatterns = [
    path('resumen/', DestinoViewSet.as_view({'get': 'resumen'}), name='destino-resumen'),   
    path('todos/', DestinoViewSet.as_view({'get': 'todos'}), name='destinos-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
