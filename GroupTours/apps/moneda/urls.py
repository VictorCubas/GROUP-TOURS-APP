from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import MonedaViewSet, CotizacionMonedaViewSet

urlpatterns = [
    # Monedas
    path('', MonedaViewSet.as_view({'get':'list', 'post':'create'}), name='moneda'),
    path('<int:pk>/', MonedaViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update'}), name='moneda-detail'),
    path('resumen/', MonedaViewSet.as_view({'get':'resumen'}), name='moneda-resumen'),
    path('todos/', MonedaViewSet.as_view({'get':'todos'}), name='moneda-todos'),

    # Cotizaciones
    path('cotizaciones/', CotizacionMonedaViewSet.as_view({'get':'list', 'post':'create'}), name='cotizacion-list'),
    path('cotizaciones/<int:pk>/', CotizacionMonedaViewSet.as_view({'get':'retrieve', 'put':'update', 'patch':'partial_update', 'delete':'destroy'}), name='cotizacion-detail'),
    path('cotizaciones/vigente/', CotizacionMonedaViewSet.as_view({'get':'vigente'}), name='cotizacion-vigente'),
    path('cotizaciones/historial/', CotizacionMonedaViewSet.as_view({'get':'historial'}), name='cotizacion-historial'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
