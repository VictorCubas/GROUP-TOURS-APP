"""
Dashboard URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    path('resumen-general/', views.resumen_general, name='dashboard-resumen-general'),
    path('alertas/', views.alertas, name='dashboard-alertas'),
    path('metricas-ventas/', views.metricas_ventas, name='dashboard-metricas-ventas'),
    path('top-destinos/', views.top_destinos, name='dashboard-top-destinos'),
]

