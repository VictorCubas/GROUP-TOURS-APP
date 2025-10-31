from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reserva.models import Pasajero
from .models import Voucher, ComprobantePagoDistribucion


def generar_voucher_si_cumple_condiciones(pasajero):
    """
    Función auxiliar que verifica si un pasajero cumple las condiciones para tener voucher
    y lo genera si corresponde.

    Condiciones:
    1. Tiene datos reales cargados (por_asignar=False)
    2. Ha pagado el 100% de su precio asignado (esta_totalmente_pagado=True)

    Returns:
        Voucher si se creó, None si no se creó o ya existía
    """
    # Verificar si el pasajero cumple las condiciones para tener voucher
    if not pasajero.por_asignar and pasajero.esta_totalmente_pagado:
        # Verificar si ya existe un voucher para este pasajero
        try:
            # Intentar obtener el voucher existente
            if hasattr(pasajero, 'voucher') and pasajero.voucher:
                print(f"[INFO] Voucher ya existe para pasajero {pasajero.id}: {pasajero.voucher.codigo_voucher}")
                return None
        except Voucher.DoesNotExist:
            pass

        # No existe voucher, crearlo
        try:
            voucher = Voucher.objects.create(pasajero=pasajero)

            # Actualizar el campo voucher_codigo en el pasajero INMEDIATAMENTE después de crear el voucher
            # Esto garantiza que el campo se actualice incluso si falla la generación del QR
            Pasajero.objects.filter(pk=pasajero.pk).update(voucher_codigo=voucher.codigo_voucher)

            # Generar código QR automáticamente
            try:
                voucher.generar_qr()
                voucher.save()
                print(f"[OK] Voucher generado: {voucher.codigo_voucher} para pasajero {pasajero.persona} (con QR)")
            except Exception as qr_error:
                # Si falla el QR, el voucher igual se crea (sin QR)
                print(f"[WARN] Voucher creado sin QR: {voucher.codigo_voucher} - Error: {qr_error}")

            return voucher
        except Exception as e:
            print(f"[ERROR] Error generando voucher para pasajero {pasajero.id}: {e}")
            return None

    return None


@receiver(post_save, sender=Pasajero)
def crear_voucher_para_pasajero_al_guardar(sender, instance, created, **kwargs):
    """
    Signal que se dispara al guardar un Pasajero.

    Se ejecuta cuando:
    - Se crea un pasajero nuevo con datos completos y pago total
    - Se actualiza un pasajero (ej: cambiar de por_asignar=True a False)

    Genera el voucher automáticamente si cumple las condiciones.
    """
    # Evitar ejecutar si estamos en una transacción de raw SQL o fixtures
    if kwargs.get('raw', False):
        return

    generar_voucher_si_cumple_condiciones(instance)


@receiver(post_save, sender=ComprobantePagoDistribucion)
def crear_voucher_para_pasajero_al_pagar(sender, instance, created, **kwargs):
    """
    Signal que se dispara cuando se crea o actualiza una ComprobantePagoDistribucion.

    Esto captura cuando se registra un pago (parcial o total) para un pasajero.
    Verifica si con este pago el pasajero ahora cumple las condiciones para tener voucher.

    Se ejecuta automáticamente en los endpoints:
    - POST /api/reservas/{id}/registrar-senia/
    - POST /api/reservas/{id}/registrar-pago/
    """
    # Evitar ejecutar si estamos en una transacción de raw SQL o fixtures
    if kwargs.get('raw', False):
        return

    # Solo verificar si el comprobante está activo (no anulado)
    if instance.comprobante.activo:
        pasajero = instance.pasajero
        print(f"[INFO] Pago registrado para pasajero {pasajero.id}. Verificando condiciones para voucher...")
        generar_voucher_si_cumple_condiciones(pasajero)
