from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ServicioViewSet

urlpatterns = [
    path('', ServicioViewSet.as_view({'get':'list', 'post':'create'}), name='servicio'),
    path('<int:pk>/', ServicioViewSet.as_view({'get':'retrieve', 'put':'update', 'patch':'partial_update'}), name='servicio-detail'),
    path('resumen/', ServicioViewSet.as_view({'get':'resumen'}), name='servicio-resumen'),   
    path('todos/', ServicioViewSet.as_view({'get':'todos'}), name='servicio-todos'),   
]

urlpatterns = format_suffix_patterns(urlpatterns)
