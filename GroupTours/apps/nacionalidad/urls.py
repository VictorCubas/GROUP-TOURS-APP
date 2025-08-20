from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', NacionalidadViewSet.as_view({'get':'list', 'post':'create',}), name='nacionalidad'),
    path('<int:pk>/', NacionalidadViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='nacionalidad-detail'),
    path('resumen/', NacionalidadViewSet.as_view({'get': 'resumen'}), name='nacionalidad-resumen'),   
    path('todos/', NacionalidadViewSet.as_view({'get': 'todos'}), name='todos'),   
]


urlpatterns = format_suffix_patterns(urlpatterns)