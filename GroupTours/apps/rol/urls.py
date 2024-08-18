from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-roles'),
    path('/agregar', views.agregar, name='agregar-permiso'),
    path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    path('/edicion/<int:id>', views.edicion, name='edicion-permiso'),
    path('/editar/<int:id>', views.editar, name='editar-permiso'),
    path('/buscar/', views.buscar, name='buscar-rol'),
]
