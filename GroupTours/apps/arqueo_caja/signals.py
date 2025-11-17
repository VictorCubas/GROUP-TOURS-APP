# apps/arqueo_caja/signals.py
"""
Señales para integración automática del arqueo de caja con otros módulos.

NOTA: La creación de MovimientoCaja desde ComprobantePago se hace directamente
en el método save() del modelo ComprobantePago (_generar_movimiento_caja).
Este signal estaba causando duplicación de movimientos.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.comprobante.models import ComprobantePago
from .services import registrar_movimiento_desde_comprobante
from .models import MovimientoCaja


# DESACTIVADO: Este signal causaba duplicación de movimientos.
# La creación de MovimientoCaja se hace en ComprobantePago.save()
# @receiver(post_save, sender=ComprobantePago)
# def crear_movimiento_caja_desde_comprobante(sender, instance, created, **kwargs):
#     """
#     Signal que se ejecuta cuando se crea o actualiza un ComprobantePago.
#
#     Si se crea un comprobante nuevo y hay una caja abierta, se registra
#     automáticamente el movimiento de caja.
#
#     Args:
#         sender: Clase ComprobantePago
#         instance: Instancia del comprobante creado/actualizado
#         created: True si es nuevo, False si se actualizó
#         **kwargs: Argumentos adicionales
#     """
#     if created:
#         # Solo registrar movimiento para comprobantes nuevos
#         try:
#             movimiento = registrar_movimiento_desde_comprobante(instance)
#
#             if movimiento:
#                 print(f"✅ Movimiento de caja creado automáticamente: {movimiento.numero_movimiento}")
#             else:
#                 print(f"ℹ️ No hay caja abierta. Comprobante {instance.numero_comprobante} sin movimiento de caja.")
#
#         except Exception as e:
#             # Log del error pero no fallar la creación del comprobante
#             print(f"⚠️ Error al crear movimiento de caja para {instance.numero_comprobante}: {str(e)}")


# DESACTIVADO: Este signal también causaba duplicación.
# La anulación de MovimientoCaja se hace en ComprobantePago.anular() -> _anular_movimiento_caja()
# @receiver(post_save, sender=ComprobantePago)
# def anular_movimiento_caja_si_comprobante_anulado(sender, instance, created, **kwargs):
#     """
#     Signal que se ejecuta cuando se actualiza un ComprobantePago.
#
#     Si el comprobante fue anulado (activo=False), también se anulan
#     los movimientos de caja asociados.
#
#     Args:
#         sender: Clase ComprobantePago
#         instance: Instancia del comprobante
#         created: True si es nuevo, False si se actualizó
#         **kwargs: Argumentos adicionales
#     """
#     if not created and not instance.activo:
#         # Comprobante fue anulado, anular movimientos asociados
#         movimientos = MovimientoCaja.objects.filter(
#             comprobante=instance,
#             activo=True
#         )
#
#         count = movimientos.count()
#         if count > 0:
#             movimientos.update(activo=False)
#             print(f"✅ {count} movimiento(s) de caja anulado(s) por anulación de comprobante {instance.numero_comprobante}")


# Opcional: Signal para cuando se elimina un comprobante (por si acaso)
@receiver(post_delete, sender=ComprobantePago)
def log_eliminacion_comprobante(sender, instance, **kwargs):
    """
    Signal que se ejecuta cuando se elimina un ComprobantePago.

    Registra la eliminación en logs (los movimientos de caja se mantienen
    para auditoría pero quedan sin comprobante asociado por la cascada).

    Args:
        sender: Clase ComprobantePago
        instance: Instancia eliminada
        **kwargs: Argumentos adicionales
    """
    print(f"⚠️ ComprobantePago eliminado: {instance.numero_comprobante}")
