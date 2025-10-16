from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import HotelViewSet, CadenaHoteleraViewSet

urlpatterns = [
    path('', HotelViewSet.as_view({'get':'list','post':'create'}), name='hotel'),
    path('<int:pk>/', HotelViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update','delete':'destroy'}), name='hotel-detail'),
    path('resumen/', HotelViewSet.as_view({'get':'resumen'}), name='hotel-resumen'),
    path('todos/', HotelViewSet.as_view({'get':'todos'}), name='hotel-todos'),
    path('cadenas/todos/', CadenaHoteleraViewSet.as_view({'get':'todos'}), name='cadena-todos'),
    path('cadenas/todos/', CadenaHoteleraViewSet.as_view({'get':'todos'}), name='cadena-todos'),
    path('por-salida/<int:salida_id>/', HotelViewSet.as_view({'get': 'por_salida'}), name='hotel-por-salida'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
