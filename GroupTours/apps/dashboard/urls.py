"""
Dashboard URLs
"""
from django.urls import path
from . import views
from . import reportes_views

urlpatterns = [
    # Dashboard (existente)
    path('resumen-general/', views.resumen_general, name='dashboard-resumen-general'),
    path('alertas/', views.alertas, name='dashboard-alertas'),
    path('metricas-ventas/', views.metricas_ventas, name='dashboard-metricas-ventas'),
    path('top-destinos/', views.top_destinos, name='dashboard-top-destinos'),
    
    # Reportes detallados JSON
    path('reportes/movimientos-cajas/', reportes_views.reporte_movimientos_cajas, name='reporte-movimientos-cajas'),
    path('reportes/paquetes/', reportes_views.reporte_paquetes, name='reporte-paquetes'),
    path('reportes/reservas/', reportes_views.reporte_reservas, name='reporte-reservas'),
    
    # Exportación PDF
    path('reportes/movimientos-cajas/exportar-pdf/', reportes_views.exportar_movimientos_pdf, name='exportar-movimientos-pdf'),
    path('reportes/paquetes/exportar-pdf/', reportes_views.exportar_paquetes_pdf, name='exportar-paquetes-pdf'),
    path('reportes/reservas/exportar-pdf/', reportes_views.exportar_reservas_pdf, name='exportar-reservas-pdf'),
    
    # Exportación Excel
    path('reportes/movimientos-cajas/exportar-excel/', reportes_views.exportar_movimientos_excel, name='exportar-movimientos-excel'),
    path('reportes/paquetes/exportar-excel/', reportes_views.exportar_paquetes_excel, name='exportar-paquetes-excel'),
    path('reportes/reservas/exportar-excel/', reportes_views.exportar_reservas_excel, name='exportar-reservas-excel'),
    
    # Exportación CSV (NUEVO)
    path('reportes/movimientos-cajas/exportar-csv/', reportes_views.exportar_movimientos_csv, name='exportar-movimientos-csv'),
]

