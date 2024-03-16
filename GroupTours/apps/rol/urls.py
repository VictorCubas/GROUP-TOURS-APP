from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-roles'),
    path('/agregar', views.agregar, name='agregar-permiso'),
    # path('/eliminar/<int:id>', views.eliminar, name='eliminar-permiso'),
    
]
