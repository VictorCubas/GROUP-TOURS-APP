from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='empleados'),
    path('/agregar', views.agregar, name='agregar-empleado'),
#     path('/eliminar/<int:id>', views.eliminar, name='eliminar-empleado'),
#     path('/edicion/<int:id>', views.edicion, name='edicion-empleado'),
#     path('/editar/<int:id>', views.editar, name='editar-empleado'),
#     path('/buscar/', views.buscar, name='buscar-empleado'),
#     path('/activar/<int:id>', views.activar, name='activar-empleado'),
]
