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

@receiver(post_save, sender='facturacion.NotaCreditoElectronica')
def actualizar_montos_reserva_desde_nc(sender, instance, created, **kwargs):
    """
    Actualiza automáticamente los montos de la reserva y el pasajero cuando se emite una NC.

    Flujo:
    1. Usuario emite NC (total o parcial)
    2. Se crea NotaCreditoElectronica
    3. Se calculan los totales y se guarda nuevamente
    4. Este signal detecta que hay total_general > 0
    5. Crea un ComprobantePago de tipo 'devolucion' con monto negativo
    6. Crea la distribución correspondiente al pasajero (si aplica)
    7. Actualiza el monto_pagado de la reserva

    Solo se ejecuta si:
    - La NC está activa
    - El total_general es mayor a 0 (indica que ya se calcularon los totales)
    - No existe ya un comprobante de devolución para esta NC (evitar duplicados)

    Args:
        sender: Clase NotaCreditoElectronica
        instance: Instancia de la NC creada/actualizada
        created: True si es nueva, False si se actualizó
        **kwargs: Argumentos adicionales

    Notas:
    - El ComprobantePago de devolución permite que Pasajero.monto_pagado se calcule automáticamente
    - La Reserva.monto_pagado se actualiza directamente (es un campo, no una property)
    """
    from decimal import Decimal

    # Solo procesar NCs activas con total calculado
    if not instance.activo or instance.total_general <= Decimal('0'):
        return

    # Obtener la factura afectada
    factura = instance.factura_afectada
    monto_nc = instance.total_general

    # Verificar que la factura tenga una reserva
    if not factura.reserva:
        print(f"⚠️ NC {instance.numero_nota_credito} sin reserva asociada. No se actualiza monto_pagado.")
        return

    reserva = factura.reserva

    # Verificar que no exista ya un comprobante de devolución para esta NC
    from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion

    comprobante_existente = ComprobantePago.objects.filter(
        reserva=reserva,
        tipo='devolucion',
        referencia=f"NC: {instance.numero_nota_credito}",
        activo=True
    ).exists()

    if comprobante_existente:
        # Ya existe un comprobante de devolución para esta NC
        return

    try:
        # ========================================
        # 1. CREAR COMPROBANTE DE DEVOLUCIÓN
        # ========================================

        # Obtener el empleado que registra (usar el responsable de la apertura de caja)
        from apps.arqueo_caja.models import AperturaCaja

        apertura = AperturaCaja.objects.filter(
            caja__punto_expedicion=instance.punto_expedicion,
            esta_abierta=True,
            activo=True
        ).first()

        if not apertura or not apertura.responsable:
            print(f"⚠️ No se encontró empleado para registrar la devolución de NC {instance.numero_nota_credito}")
            print(f"   NOTA: reserva.monto_pagado ahora se calcula automáticamente desde los pasajeros.")
            print(f"   La NC se reflejará automáticamente en Pasajero.monto_pagado.")

            # NOTA: Ya NO necesitamos actualizar reserva.monto_pagado manualmente
            # porque ahora es una propiedad calculada que suma los monto_pagado de los pasajeros.
            # Pasajero.monto_pagado ya resta las NC automáticamente.

            print(f"✅ La NC se reflejará automáticamente en la reserva:")
            print(f"   📋 Reserva: {reserva.codigo}")
            print(f"   💰 Monto NC: Gs. {monto_nc:,.0f}")
            print(f"   ℹ️  El monto_pagado de los pasajeros ya considera esta NC.")
            return

        empleado = apertura.responsable

        # Crear el comprobante de devolución
        # NOTA: El monto debe ser el valor ABSOLUTO positivo, la suma/resta se maneja en actualizar_monto_reserva()
        comprobante_devolucion = ComprobantePago.objects.create(
            reserva=reserva,
            tipo='devolucion',
            monto=monto_nc,  # Monto POSITIVO (representa cantidad devuelta)
            metodo_pago='efectivo',  # Por defecto efectivo
            referencia=f"NC: {instance.numero_nota_credito}",
            observaciones=f"Devolución por Nota de Crédito {instance.tipo_nota}\nFactura afectada: {factura.numero_factura}",
            empleado=empleado,
            activo=True
        )

        print(f"[OK] Comprobante de devolucion creado:")
        print(f"   Comprobante: {comprobante_devolucion.numero_comprobante}")
        print(f"   Monto: Gs. {comprobante_devolucion.monto:,.0f}")
        print(f"   NC: {instance.numero_nota_credito}")

        # ========================================
        # 2. CREAR DISTRIBUCIÓN AL PASAJERO (si aplica)
        # ========================================
        if factura.pasajero:
            pasajero = factura.pasajero

            # Crear distribución para el pasajero
            # NOTA: Usar monto NEGATIVO porque Pasajero.monto_pagado suma todas las distribuciones
            # sin filtrar por tipo de comprobante, entonces el monto negativo se resta automáticamente
            distribucion = ComprobantePagoDistribucion.objects.create(
                comprobante=comprobante_devolucion,
                pasajero=pasajero,
                monto=-monto_nc,  # Monto NEGATIVO para que se reste al calcular monto_pagado
                observaciones=f"Devolución por NC {instance.numero_nota_credito}"
            )

            print(f"[OK] Distribucion de devolucion creada:")
            print(f"   Pasajero: {pasajero.persona.nombre} {pasajero.persona.apellido} (ID: {pasajero.id})")
            print(f"   Monto: Gs. {distribucion.monto:,.0f}")

            # Refrescar pasajero para obtener monto_pagado actualizado
            pasajero.refresh_from_db()
            print(f"   Nuevo monto pagado: Gs. {pasajero.monto_pagado:,.0f}")
            print(f"   Nuevo saldo pendiente: Gs. {pasajero.saldo_pendiente:,.0f}")

        # ========================================
        # 3. ACTUALIZAR RESERVA usando el método oficial
        # ========================================
        # El método actualizar_monto_reserva() ya maneja correctamente las devoluciones
        comprobante_devolucion.actualizar_monto_reserva()

        # Refrescar para mostrar valores actualizados
        reserva.refresh_from_db()

        print(f"[OK] Reserva actualizada:")
        print(f"   Reserva: {reserva.codigo} (ID: {reserva.id})")
        print(f"   Monto pagado: Gs. {reserva.monto_pagado:,.0f}")
        print(f"   Saldo pendiente: Gs. {reserva.saldo_pendiente:,.0f}")

    except Exception as e:
        # No fallar si hay error al actualizar (la NC ya fue creada)
        print(f"❌ Error al crear comprobante de devolución para NC {instance.numero_nota_credito}:")
        print(f"   {str(e)}")
        print(f"   💡 Los montos deberán ajustarse manualmente.")
        import traceback
        traceback.print_exc()
