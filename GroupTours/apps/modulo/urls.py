from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', ModuloListViewSet.as_view({'get':'list', 'post':'create',}), name='modulo'),
    path('<int:pk>/', ModuloListViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='modulo-detail'),
    path('resumen/', ModuloListViewSet.as_view({'get': 'resumen'}), name='modulo-resumen'),   
    path('todos/', ModuloListViewSet.as_view({'get': 'todos'}), name='todos'),   
]


urlpatterns = format_suffix_patterns(urlpatterns)