from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-roles'),
    path('/agregar', views.agregar, name='agregar-rol'),
    path('/eliminar/<int:id>', views.eliminar, name='eliminar-rol'),
    path('/edicion/<int:id>', views.edicion, name='edicion-rol'),
    path('/editar/<int:id>', views.editar, name='editar-rol'),
    path('/buscar/', views.buscar, name='buscar-rol'),
    path('/activar/<int:id>', views.activar, name='activar-rol'),
]
