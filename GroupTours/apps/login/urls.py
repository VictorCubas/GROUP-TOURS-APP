from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index-login'),
    # path('home', views.iniciarSesion, name='iniciar-sesion'),

]
