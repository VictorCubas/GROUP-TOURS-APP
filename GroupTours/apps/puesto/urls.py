from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('resumen/', PuestoViewSet.as_view({'get': 'resumen'}), name='puesto-resumen'),   
    path('todos/', PuestoViewSet.as_view({'get': 'todos'}), name='todos'),   
]


urlpatterns = format_suffix_patterns(urlpatterns)