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


# =============================================================================
# INTEGRACIÓN: NOTAS DE CRÉDITO → MOVIMIENTOS DE CAJA
# =============================================================================

# DESACTIVADO: Este signal causaba duplicación de movimientos de caja.
# Cuando se emite una NC, el signal actualizar_montos_reserva_desde_nc ya crea
# un ComprobantePago de tipo 'devolucion', y ComprobantePago.save() automáticamente
# llama a _generar_movimiento_caja(), lo que genera el MovimientoCaja asociado.
# Por lo tanto, este signal es REDUNDANTE y causaba que se crearan 2 movimientos:
#   1. Un movimiento SIN comprobante (este signal)
#   2. Un movimiento CON comprobante (desde ComprobantePago.save())
# Fecha desactivación: 2025-11-19
#
# @receiver(post_save, sender='facturacion.NotaCreditoElectronica')
def _crear_movimiento_caja_desde_nota_credito_DESACTIVADO(sender, instance, created, **kwargs):
    """
    Registra automáticamente un egreso de caja cuando se emite una Nota de Crédito.

    Flujo:
    1. Usuario emite NC (total o parcial)
    2. Se valida que hay caja abierta (en generar_nota_credito_*)
    3. Se crea NotaCreditoElectronica
    4. Se calculan los totales y se guarda nuevamente (este signal se ejecuta aquí)
    5. Se crea MovimientoCaja de tipo "egreso" con concepto "devolucion"

    Solo se ejecuta si:
    - La NC está activa
    - El total_general es mayor a 0 (indica que ya se calcularon los totales)
    - No existe ya un movimiento para esta NC

    NOTA: Dado que ahora generar_nota_credito_total/parcial validan que hay caja abierta,
    esta señal SIEMPRE encontrará una caja abierta.

    Args:
        sender: Clase NotaCreditoElectronica
        instance: Instancia de la NC creada/actualizada
        created: True si es nueva, False si se actualizó
        **kwargs: Argumentos adicionales

    Notas:
    - El método de pago se registra como 'efectivo' por defecto
    - El movimiento se asocia al responsable de la apertura
    - La referencia incluye el número de NC y factura afectada
    """
    # Importar aquí para evitar imports circulares
    from apps.arqueo_caja.models import AperturaCaja, MovimientoCaja
    from decimal import Decimal

    # Solo procesar NCs activas con total calculado
    if not instance.activo or instance.total_general <= Decimal('0'):
        return

    # Verificar si ya existe un movimiento para esta NC (evitar duplicados)
    movimiento_existente = MovimientoCaja.objects.filter(
        referencia=f"NC: {instance.numero_nota_credito}",
        activo=True
    ).exists()

    if movimiento_existente:
        # Ya existe un movimiento, no crear duplicado
        return

    # Buscar caja abierta del punto de expedición de la NC
    # NOTA: SIEMPRE debe existir porque generar_nota_credito_* lo valida
    apertura = AperturaCaja.objects.filter(
        caja__punto_expedicion=instance.punto_expedicion,
        esta_abierta=True,
        activo=True
    ).first()

    if not apertura:
        # Esto NO debería ocurrir nunca gracias a la validación previa
        print(f"⚠️ ADVERTENCIA: NC {instance.numero_nota_credito} creada sin caja abierta.")
        print(f"   Esto indica que se creó la NC sin usar generar_nota_credito_total/parcial.")
        return

    try:
        # Crear movimiento de egreso
        movimiento = MovimientoCaja.objects.create(
            apertura_caja=apertura,
            tipo_movimiento='egreso',
            concepto='devolucion',
            monto=instance.total_general,
            metodo_pago='efectivo',  # Por defecto efectivo - TODO: mejorar inferencia
            referencia=f"NC: {instance.numero_nota_credito}",
            descripcion=(
                f"Devolución por Nota de Crédito {instance.tipo_nota}\n"
                f"Factura afectada: {instance.factura_afectada.numero_factura}\n"
                f"Motivo: {instance.motivo}"
            ),
            usuario_registro=apertura.responsable,
            fecha_hora_movimiento=instance.fecha_emision
        )

        print(f"✅ Movimiento de caja creado desde NC:")
        print(f"   📄 NC: {instance.numero_nota_credito}")
        print(f"   💰 Monto: Gs. {instance.total_general:,.0f}")
        print(f"   🧾 Movimiento: {movimiento.numero_movimiento}")
        print(f"   📦 Caja: {apertura.caja.nombre}")

    except Exception as e:
        # No fallar si hay error al crear movimiento (la NC ya fue creada)
        print(f"❌ Error al crear movimiento de caja para NC {instance.numero_nota_credito}:")
        print(f"   {str(e)}")
        print(f"   💡 El movimiento deberá registrarse manualmente.")


# =============================================================================
# INTEGRACIÓN: NOTAS DE CRÉDITO → ACTUALIZACIÓN DE RESERVAS Y PASAJEROS
# =============================================================================
#
# DESACTIVADO: 2025-11-24
# Razón: Causaba duplicación de movimientos de egreso.
# 
# Flujo correcto ahora:
# 1. Cancelar reserva → Genera ComprobantePago devolución → Movimiento de egreso
# 2. Generar NC → NO genera movimiento automático (solo anula la factura)
#
# Este signal creaba automáticamente un ComprobantePago de devolución al emitir NC,
# lo que generaba un SEGUNDO movimiento de egreso innecesario.
# Fecha desactivación: 2025-11-24
#
# @receiver(post_save, sender='facturacion.NotaCreditoElectronica')
def actualizar_montos_reserva_desde_nc_DESACTIVADO(sender, instance, created, **kwargs):
    """
    DESACTIVADO - Antes actualizaba automáticamente los montos de la reserva al emitir NC.

    Flujo ANTERIOR (ya no se usa):
    1. Usuario emite NC (total o parcial)
    2. Se crea NotaCreditoElectronica
    3. Se calculan los totales y se guarda nuevamente
    4. Este signal detecta que hay total_general > 0
    5. Crea un ComprobantePago de tipo 'devolucion' con monto negativo
    6. Crea la distribución correspondiente al pasajero (si aplica)
    7. Actualiza el monto_pagado de la reserva

    PROBLEMA: Causaba duplicación de movimientos de egreso.
    - Movimiento 1: Al cancelar reserva (correcto)
    - Movimiento 2: Al emitir NC (duplicado e incorrecto)

    SOLUCIÓN: Desactivar este signal. Las devoluciones se manejan solo al cancelar.
    """
    # SIGNAL DESACTIVADO - No hacer nada
    # Las devoluciones ahora se manejan exclusivamente al cancelar la reserva
    return
