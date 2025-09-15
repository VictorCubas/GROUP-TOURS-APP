# apps/ubicaciones/urls.py
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import CiudadViewSet

urlpatterns = [
    path('', CiudadViewSet.as_view({'get': 'list', 'post': 'create'}), name='ciudad'),
    path('<int:pk>/', CiudadViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
        'patch': 'partial_update'
    }), name='ciudad-detail'),
    path('resumen/', CiudadViewSet.as_view({'get': 'resumen'}), name='ciudad-resumen'),
    path('todos/', CiudadViewSet.as_view({'get': 'todos'}), name='ciudad-todos'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
