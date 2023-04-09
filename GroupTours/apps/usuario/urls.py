from django.urls import path
from .views import UsuarioList

urlpatterns = [
    # path('usuarios/', UsuarioList.index, name='index'),
    path('api/usuarios/', UsuarioList.as_view({'get':'list', 'post':'create'})),
]