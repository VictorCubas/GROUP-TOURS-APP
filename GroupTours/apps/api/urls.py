from django.urls import path, include

urlpatterns = [
    path('login/', include('apps.login_token.urls')),
    path('roles/', include('apps.rol.urls')),
    path('permisos/', include('apps.permiso.urls')),
    path('modulos/', include('apps.modulo.urls')),
    path('tipo_documentos/', include('apps.tipo_documento.urls')),
    path('personas/', include('apps.persona.urls')),
    path('nacionalidades/', include('apps.nacionalidad.urls')),
    path('puestos/', include('apps.puesto.urls')),
    path('tipo_remuneracion/', include('apps.tipo_remuneracion.urls')),
    path('empleados/', include('apps.empleado.urls')),
    path('usuarios/', include('apps.usuario.urls')),
    path('facturacion/', include('apps.facturacion.urls')),
    path('distribuidora/', include('apps.distribuidora.urls')),
    path('destino/', include('apps.destino.urls')),
    # Puedes seguir agregando aquí otras rutas
]