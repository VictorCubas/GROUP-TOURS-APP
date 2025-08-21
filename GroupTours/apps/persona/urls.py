from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', PersonaViewSet.as_view({'get':'list', 'post':'create',}), name='persona'),
    path('<int:pk>/', PersonaViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='persona-detail'),
    path('resumen/',PersonaViewSet.as_view({'get': 'resumen'}), name='persona-resumen'),   
    path('todos/', PersonaViewSet.as_view({'get': 'todos'}), name='todos'),   
]


urlpatterns = format_suffix_patterns(urlpatterns)