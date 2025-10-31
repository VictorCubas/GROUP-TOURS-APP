"""
Script para generar vouchers de pasajeros que ya cumplen las condiciones.

Este script debe ejecutarse UNA VEZ después de la migración para generar
vouchers de todos los pasajeros que ya tienen:
1. Datos reales cargados (por_asignar=False)
2. Pago completo (esta_totalmente_pagado=True)
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Pasajero
from apps.comprobante.models import Voucher


def generar_vouchers_faltantes():
    """
    Genera vouchers para todos los pasajeros que cumplen las condiciones
    pero aún no tienen voucher.
    """
    print("\n" + "="*80)
    print("GENERANDO VOUCHERS PARA PASAJEROS QUE CUMPLEN LAS CONDICIONES")
    print("="*80 + "\n")

    # Buscar pasajeros que cumplen condiciones pero no tienen voucher
    pasajeros_sin_voucher = Pasajero.objects.filter(
        por_asignar=False  # Tienen datos reales
    ).exclude(
        voucher__isnull=False  # No tienen voucher ya creado
    )

    total_candidatos = 0
    vouchers_creados = 0
    sin_pago_completo = 0

    for pasajero in pasajeros_sin_voucher:
        total_candidatos += 1

        # Verificar si el pasajero tiene pago completo
        if pasajero.esta_totalmente_pagado:
            try:
                # Crear voucher
                voucher = Voucher.objects.create(pasajero=pasajero)

                # Generar QR
                try:
                    voucher.generar_qr()
                    voucher.save()
                except Exception as qr_error:
                    print(f"  [WARN] Voucher creado sin QR para {pasajero.persona}: {qr_error}")

                # Actualizar voucher_codigo en pasajero
                Pasajero.objects.filter(pk=pasajero.pk).update(voucher_codigo=voucher.codigo_voucher)

                vouchers_creados += 1
                print(f"  [OK] Voucher creado: {voucher.codigo_voucher} - {pasajero.persona}")

            except Exception as e:
                print(f"  [ERROR] Error creando voucher para {pasajero.persona}: {e}")
        else:
            sin_pago_completo += 1
            saldo = pasajero.saldo_pendiente
            print(f"  [INFO] {pasajero.persona} - Saldo pendiente: ${saldo} (no se genera voucher)")

    print("\n" + "-"*80)
    print(f"RESUMEN:")
    print(f"   - Total de pasajeros con datos reales: {total_candidatos}")
    print(f"   - Vouchers creados: {vouchers_creados}")
    print(f"   - Pasajeros sin pago completo: {sin_pago_completo}")
    print("-"*80 + "\n")

    return vouchers_creados


if __name__ == '__main__':
    try:
        total = generar_vouchers_faltantes()
        print(f"\n[OK] Proceso completado exitosamente. Se generaron {total} vouchers.\n")
    except Exception as e:
        print(f"\n[ERROR] Error durante el proceso: {e}\n")
        import traceback
        traceback.print_exc()
