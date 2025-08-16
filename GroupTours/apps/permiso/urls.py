from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', PermisoListViewSet.as_view({'get':'list', 'post':'create',}), name='permiso'),
    path('<int:pk>/', PermisoListViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='permiso-detail'),
    path('resumen/', PermisoListViewSet.as_view({'get': 'resumen'}), name='permiso-resumen'), 
    path('todos/', PermisoListViewSet.as_view({'get': 'todos'}), name='todos'),
]


urlpatterns = format_suffix_patterns(urlpatterns)