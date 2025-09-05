from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import DistribuidoraViewSet

urlpatterns = [
    path('resumen/', DistribuidoraViewSet.as_view({'get': 'resumen'}), name='distribuidora-resumen'),   
    path('todos/', DistribuidoraViewSet.as_view({'get': 'todos'}), name='distribuidoras-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
