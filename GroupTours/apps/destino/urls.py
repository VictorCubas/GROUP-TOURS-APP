from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import DestinoViewSet

urlpatterns = [
    path('', DestinoViewSet.as_view({'get':'list','post':'create'}), name='destino'),
    path('<int:pk>/', DestinoViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update','delete':'destroy'}), name='destino-detail'),
    path('resumen/', DestinoViewSet.as_view({'get':'resumen'}), name='destino-resumen'),   
    path('todos/', DestinoViewSet.as_view({'get':'todos'}), name='destino-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
