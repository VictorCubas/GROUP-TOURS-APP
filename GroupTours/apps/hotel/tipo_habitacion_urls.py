from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from .views import TipoHabitacionViewSet

urlpatterns = [
    path('', TipoHabitacionViewSet.as_view({'get':'list','post':'create'}), name='tipo-habitacion'),
    path('<int:pk>/', TipoHabitacionViewSet.as_view({'get':'retrieve','put':'update','patch':'partial_update','delete':'destroy'}), name='tipo-habitacion-detail'),
    path('resumen/', TipoHabitacionViewSet.as_view({'get':'resumen'}), name='tipo-habitacion-resumen'),
    path('todos/', TipoHabitacionViewSet.as_view({'get':'todos'}), name='tipo-habitacion-todos'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
