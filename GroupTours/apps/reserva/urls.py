from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import ReservaViewSet

urlpatterns = [
    path('', ReservaViewSet.as_view({'get': 'list', 'post': 'create'}), name='reserva'),
    path('<int:pk>/', ReservaViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update'}), name='reserva-detail'),
    path('resumen/', ReservaViewSet.as_view({'get': 'resumen'}), name='reserva-resumen'),
    path('todos/', ReservaViewSet.as_view({'get': 'todos'}), name='reserva-todos'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
