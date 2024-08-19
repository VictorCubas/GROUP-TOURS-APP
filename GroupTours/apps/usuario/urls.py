from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-usuario'),
    path('/registrarUsuario', views.registrarUsuario, name='registrar-usuario'),
    path('/eliminar/<int:id>', views.eliminar, name='eliminar-usuario'),
    
]