from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', EmpleadoViewSet.as_view({'get':'list', 'post':'create',}), name='empleado'),
    path('<int:pk>/', EmpleadoViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='empleado-detail'),
    path('resumen/', EmpleadoViewSet.as_view({'get': 'resumen'}), name='empleado-resumen'), 
    path('todos/', EmpleadoViewSet.as_view({'get': 'todos'}), name='todos'),
]


urlpatterns = format_suffix_patterns(urlpatterns)