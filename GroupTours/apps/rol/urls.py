from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-roles'),
    # path('/registrarPermiso', views.registrarPermiso, name='registrar-permiso'),
    # path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    
]
