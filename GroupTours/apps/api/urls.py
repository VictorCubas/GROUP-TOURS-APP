from django.urls import path, include

urlpatterns = [
    path('login/', include('apps.login_token.urls')),
    path('permisos/', include('apps.permiso.urls')),
    path('modulos/', include('apps.modulo.urls')),
    # Puedes seguir agregando aquí otras rutas
]