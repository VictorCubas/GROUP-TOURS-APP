from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import UsuarioViewSet

urlpatterns = [
    path('', UsuarioViewSet.as_view({'get':'list', 'post':'create'}), name='usuario'),
    path('<int:pk>/', UsuarioViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='usuario-detail'),
    path('resumen/', UsuarioViewSet.as_view({'get': 'resumen'}), name='usuario-resumen'),
    path('resetear/', UsuarioViewSet.as_view({'post': 'resetear'}), name='resetear-contrasenia'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
