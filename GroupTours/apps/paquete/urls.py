from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import PaqueteViewSet

urlpatterns = [
    path('', PaqueteViewSet.as_view({'get': 'list', 'post': 'create'}), name='paquete'),
    path('<int:pk>/', PaqueteViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='paquete-detail'),
    path('resumen/', PaqueteViewSet.as_view({'get': 'resumen'}), name='paquete-resumen'),   
    path('todos/', PaqueteViewSet.as_view({'get': 'todos'}), name='paquete-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
