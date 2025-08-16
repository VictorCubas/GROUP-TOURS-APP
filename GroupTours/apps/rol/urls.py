from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', RolListViewSet.as_view({'get':'list', 'post':'create',}), name='rol'),
    path('<int:pk>/', RolListViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='rol-detail'),
    path('resumen/', RolListViewSet.as_view({'get': 'resumen'}), name='rol-resumen'),
]


urlpatterns = format_suffix_patterns(urlpatterns)