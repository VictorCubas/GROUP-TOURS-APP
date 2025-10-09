from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ZonaGeograficaViewSet

urlpatterns = [
    path('', ZonaGeograficaViewSet.as_view({'get':'list','post':'create'}), name='zona-geografica'),
    path('<int:pk>/', ZonaGeograficaViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update','delete':'destroy'}), name='zona-geografica-detail'),
    path('resumen/', ZonaGeograficaViewSet.as_view({'get':'resumen'}), name='zona-geografica-resumen'),
    path('todos/', ZonaGeograficaViewSet.as_view({'get':'todos'}), name='zona-geografica-todos'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
