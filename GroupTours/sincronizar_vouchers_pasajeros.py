"""
Script para sincronizar el campo voucher_codigo en pasajeros que ya tienen voucher generado.

Este script es necesario después de corregir el signal de generación de vouchers,
para actualizar los pasajeros que ya tienen voucher pero no tienen el campo voucher_codigo actualizado.

Uso:
    python sincronizar_vouchers_pasajeros.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.comprobante.models import Voucher
from apps.reserva.models import Pasajero


def sincronizar_vouchers():
    """
    Sincroniza el campo voucher_codigo en los pasajeros que tienen voucher
    pero el campo está en null.
    """
    print("=" * 80)
    print("SINCRONIZACION DE VOUCHERS EN PASAJEROS")
    print("=" * 80)
    print()

    # Obtener todos los vouchers activos que tienen pasajero
    vouchers = Voucher.objects.filter(activo=True, pasajero__isnull=False)
    total_vouchers = vouchers.count()

    print(f"[INFO] Total de vouchers activos con pasajero: {total_vouchers}")
    print()

    actualizados = 0
    ya_sincronizados = 0
    errores = 0

    for voucher in vouchers:
        try:
            pasajero = voucher.pasajero

            # Verificar si el campo voucher_codigo está vacío o diferente
            if not pasajero.voucher_codigo or pasajero.voucher_codigo != voucher.codigo_voucher:
                # Actualizar usando update para evitar disparar signals
                Pasajero.objects.filter(pk=pasajero.pk).update(
                    voucher_codigo=voucher.codigo_voucher
                )
                print(f"[OK] Pasajero {pasajero.id} actualizado: {voucher.codigo_voucher}")
                actualizados += 1
            else:
                print(f"[SKIP] Pasajero {pasajero.id} ya sincronizado: {voucher.codigo_voucher}")
                ya_sincronizados += 1

        except Exception as e:
            print(f"[ERROR] Error procesando voucher {voucher.id}: {e}")
            errores += 1

    print()
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Total de vouchers procesados: {total_vouchers}")
    print(f"[OK] Pasajeros actualizados: {actualizados}")
    print(f"[SKIP] Pasajeros ya sincronizados: {ya_sincronizados}")
    print(f"[ERROR] Errores: {errores}")
    print()

    if actualizados > 0:
        print("[SUCCESS] Sincronizacion completada exitosamente!")
    elif ya_sincronizados == total_vouchers:
        print("[SUCCESS] Todos los pasajeros ya estaban sincronizados.")
    else:
        print("[WARNING] Sincronizacion completada con algunos errores.")


if __name__ == "__main__":
    sincronizar_vouchers()
