# apps/arqueo_caja/urls.py
from rest_framework.routers import DefaultRouter
from .views import CajaViewSet, AperturaCajaViewSet, MovimientoCajaViewSet, CierreCajaViewSet

router = DefaultRouter()

router.register(r'cajas', CajaViewSet, basename='caja')
router.register(r'aperturas', AperturaCajaViewSet, basename='apertura')
router.register(r'movimientos', MovimientoCajaViewSet, basename='movimiento')
router.register(r'cierres', CierreCajaViewSet, basename='cierre')

urlpatterns = router.urls
