from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.reserva.models import Reserva
from .models import Voucher


@receiver(post_save, sender=Reserva)
def crear_voucher_al_confirmar(sender, instance, created, **kwargs):
    """
    Crea automáticamente un voucher cuando una reserva pasa a estado 'confirmada'.
    Solo se crea si no existe un voucher previo para evitar duplicados.
    """
    # Solo crear voucher si la reserva está confirmada
    if instance.estado == 'confirmada':
        # Verificar si ya existe un voucher para esta reserva
        if not hasattr(instance, 'voucher'):
            try:
                voucher = Voucher.objects.create(reserva=instance)
                # Generar código QR automáticamente
                try:
                    voucher.generar_qr()
                    voucher.save()
                    print(f"[OK] Voucher generado: {voucher.codigo_voucher}")
                except Exception as qr_error:
                    # Si falla el QR, el voucher igual se crea (sin QR)
                    print(f"[WARN] Voucher creado sin QR: {qr_error}")
            except Exception as e:
                print(f"[ERROR] Error generando voucher para {instance.codigo}: {e}")
