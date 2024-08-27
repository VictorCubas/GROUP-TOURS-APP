from django.urls import path
from . import views

urlpatterns = [
    path('/terrestres', views.index, name='index-paquete'),
    # path('/registrarPermiso', views.registrarPermiso, name='registrar-permiso'),
    # path('/edicionPermiso/<int:codigo>', views.edicionPermiso, name='edicion-permiso'),
    # path('/editarPermiso/<int:id>', views.editarPermiso, name='editar-permiso'),
    # path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    # path('/buscar/', views.buscar, name='buscar-permiso'),
    # path('/activar/<int:id>', views.activar, name='activar-permiso'),
    
]
