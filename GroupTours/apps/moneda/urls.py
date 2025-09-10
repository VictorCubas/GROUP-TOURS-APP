from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import MonedaViewSet

urlpatterns = [
    path('', MonedaViewSet.as_view({'get':'list', 'post':'create'}), name='moneda'),
    path('<int:pk>/', MonedaViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update'}), name='moneda-detail'),
    path('resumen/', MonedaViewSet.as_view({'get':'resumen'}), name='moneda-resumen'),
    path('todos/', MonedaViewSet.as_view({'get':'todos'}), name='moneda-todos'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
