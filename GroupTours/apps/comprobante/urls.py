from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ComprobantePagoViewSet,
    ComprobantePagoDistribucionViewSet,
    VoucherViewSet,
)

router = DefaultRouter()
router.register(r'comprobantes', ComprobantePagoViewSet, basename='comprobante')
router.register(r'distribuciones', ComprobantePagoDistribucionViewSet, basename='distribucion')
router.register(r'vouchers', VoucherViewSet, basename='voucher')

urlpatterns = [
    path('', include(router.urls)),
]
