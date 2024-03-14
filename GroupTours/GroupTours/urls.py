"""GroupTours URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.login.urls')),
<<<<<<< HEAD
    path('home', include('apps.home.urls')),
    path('logout', include('apps.logout.urls')),
    path('permiso', include('apps.permiso.urls')),
=======
    path('', include('apps.usuario.urls')),
    path('usuarios/', include('apps.users.urls')),
>>>>>>> 6cb9efa5c264a4d9814222c04185d6a2bf212cfe
]
