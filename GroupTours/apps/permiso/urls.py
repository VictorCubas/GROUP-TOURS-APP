from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-permiso'),
    path('/registrarPermiso', views.registrarPermiso, name='registrar-permiso'),
    path('/edicionPermiso/<int:codigo>', views.edicionPermiso, name='edicion-permiso'),
    path('/editarPermiso/<int:id>', views.editarPermiso, name='editar-permiso'),
    path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    path('/buscar/', views.buscar, name='buscar-permiso'),
    
]
