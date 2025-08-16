from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', TipoDocumentoViewSet.as_view({'get':'list', 'post':'create',}), name='tipo-documento'),
    path('<int:pk>/', TipoDocumentoViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='tipo-documento-detail'),
    path('resumen/', TipoDocumentoViewSet.as_view({'get': 'resumen'}), name='tipo-documento-resumen'),   
    path('todos/', TipoDocumentoViewSet.as_view({'get': 'todos'}), name='todos'),   
]


urlpatterns = format_suffix_patterns(urlpatterns)