from django.urls import re_path, path, include
from rest_framework.urlpatterns import format_suffix_patterns
from .views import *

urlpatterns = [
    path('', PermisoListViewSet.as_view({'get':'list', 'post':'create',}), name='permiso'),
    path('<int:pk>/', PermisoListViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='permiso-detail'),
    # path('<int:pk>/', PermisoListViewSet.actualizar, name='actualizar-permiso'),
    # path('/registrarPermiso', views.registrarPermiso, name='registrar-permiso'),
    # path('/edicionPermiso/<int:codigo>', views.edicionPermiso, name='edicion-permiso'),
    # path('/editarPermiso/<int:id>', views.editarPermiso, name='editar-permiso'),
    # path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    # path('/buscar/', views.buscar, name='buscar-permiso'),
    # path('/activar/<int:id>', views.activar, name='activar-permiso'),
    
]


urlpatterns = format_suffix_patterns(urlpatterns)