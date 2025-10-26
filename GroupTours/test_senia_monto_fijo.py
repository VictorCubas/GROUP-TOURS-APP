"""
Script de prueba para validar el cálculo correcto de seña como MONTO FIJO.

Este script verifica que:
1. SalidaPaquete.senia es un monto fijo (ej: 1500.00)
2. Reserva.seña_total = salida.senia × cantidad_pasajeros
3. Pasajero.seña_requerida = salida.senia (monto fijo por pasajero)
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from decimal import Decimal
from apps.reserva.models import Reserva, Pasajero
from apps.paquete.models import SalidaPaquete


def test_senia_monto_fijo():
    """
    Prueba que la seña se calcula correctamente como monto fijo.
    """
    print("=" * 80)
    print("TEST: Cálculo de Seña como Monto Fijo")
    print("=" * 80)

    # Buscar una reserva que tenga salida con seña configurada
    reserva = Reserva.objects.filter(
        salida__senia__isnull=False,
        salida__activo=True,
        activo=True
    ).select_related('salida', 'salida__paquete').first()

    if not reserva:
        print("\nERROR: No se encontro ninguna reserva con salida que tenga senia configurada.")
        print("   Crea una reserva con una salida que tenga senia configurada.")
        return

    salida = reserva.salida

    print(f"\nSalida de Paquete: {salida}")
    print(f"   - Paquete: {salida.paquete.nombre}")
    print(f"   - Fecha salida: {salida.fecha_salida}")
    print(f"   - Senia (monto fijo por pasajero): ${salida.senia}")

    print(f"\nReserva: {reserva.codigo}")
    print(f"   - Estado: {reserva.estado}")
    print(f"   - Cantidad de pasajeros: {reserva.cantidad_pasajeros}")
    print(f"   - Precio unitario: ${reserva.precio_unitario}")
    print(f"   - Precio total: ${reserva.costo_total_estimado}")

    # CÁLCULO DE SEÑA TOTAL
    senia_calculada = salida.senia * reserva.cantidad_pasajeros if salida.senia else Decimal("0")
    print(f"\nCALCULO DE SENIA TOTAL:")
    print(f"   - Senia por pasajero: ${salida.senia}")
    print(f"   - Cantidad pasajeros: {reserva.cantidad_pasajeros}")
    print(f"   - Senia total calculada: ${senia_calculada}")
    print(f"   - Senia total (propiedad): ${reserva.seña_total}")

    # Validación
    if reserva.seña_total == senia_calculada:
        print(f"   [OK] CORRECTO: senia_total coincide")
    else:
        print(f"   [ERROR] senia_total no coincide")

    # ESTADO DE PAGO
    saldo_reserva = reserva.costo_total_estimado - reserva.monto_pagado
    print(f"\nESTADO DE PAGO:")
    print(f"   - Monto pagado: ${reserva.monto_pagado}")
    print(f"   - Senia requerida: ${reserva.seña_total}")
    print(f"   - Saldo pendiente: ${saldo_reserva}")
    print(f"   - Puede confirmarse: {reserva.puede_confirmarse()}")

    # DESGLOSE POR PASAJERO
    pasajeros = reserva.pasajeros.all()
    if pasajeros.exists():
        print(f"\nDESGLOSE POR PASAJERO:")
        for i, pasajero in enumerate(pasajeros, 1):
            nombre_completo = f"{pasajero.persona.nombre} {pasajero.persona.apellido}"
            print(f"\n   Pasajero {i}: {nombre_completo}")
            print(f"   - Precio asignado: ${pasajero.precio_asignado}")
            print(f"   - Senia requerida (FIJA): ${pasajero.seña_requerida}")
            print(f"   - Monto pagado: ${pasajero.monto_pagado}")
            print(f"   - Saldo pendiente: ${pasajero.saldo_pendiente}")
            print(f"   - Tiene senia pagada: {'SI' if pasajero.tiene_sena_pagada else 'NO'}")
            print(f"   - Porcentaje pagado: {pasajero.porcentaje_pagado}%")

            # Validación: seña_requerida debe ser igual a salida.senia
            if pasajero.seña_requerida == salida.senia:
                print(f"   [OK] CORRECTO: senia_requerida = ${salida.senia} (monto fijo)")
            else:
                print(f"   [ERROR] senia_requerida deberia ser ${salida.senia}")
    else:
        print(f"\nADVERTENCIA: No hay pasajeros cargados en esta reserva")

    # EJEMPLO DE CÁLCULO PARA FRONTEND
    print("\n" + "=" * 80)
    print("EJEMPLO DE DATOS PARA FRONTEND:")
    print("=" * 80)

    ejemplo = {
        "salida": {
            "id": salida.id,
            "paquete": salida.paquete.nombre,
            "fecha_salida": str(salida.fecha_salida),
            "senia_por_pasajero": float(salida.senia) if salida.senia else 0,
            "precio_venta_min": float(salida.precio_venta_sugerido_min) if salida.precio_venta_sugerido_min else 0,
            "precio_venta_max": float(salida.precio_venta_sugerido_max) if salida.precio_venta_sugerido_max else 0,
        },
        "reserva": {
            "codigo": reserva.codigo,
            "cantidad_pasajeros": reserva.cantidad_pasajeros,
            "precio_unitario": float(reserva.precio_unitario) if reserva.precio_unitario else 0,
            "precio_total": float(reserva.costo_total_estimado),
            "senia_total_requerida": float(reserva.seña_total),
            "monto_pagado": float(reserva.monto_pagado),
            "saldo_pendiente": float(saldo_reserva),
        },
        "calculo": {
            "formula_senia_total": f"{salida.senia} × {reserva.cantidad_pasajeros} = {reserva.seña_total}",
            "saldo_despues_senia": float(reserva.costo_total_estimado - reserva.seña_total),
        }
    }

    import json
    print(json.dumps(ejemplo, indent=2, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("[OK] TEST COMPLETADO")
    print("=" * 80)


if __name__ == "__main__":
    test_senia_monto_fijo()
