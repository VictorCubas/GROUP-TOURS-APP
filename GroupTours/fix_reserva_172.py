"""
Script para corregir la reserva 172 que tiene pasajeros pendientes de más.

La reserva tiene:
- cantidad_pasajeros: 3
- pasajeros reales: 4 (Victor Cubas + Por Asignar 1, 2, 3)

Se debe eliminar "Por Asignar 1" y sus pagos asociados.
"""

from apps.reserva.models import Pasajero, Reserva
from apps.comprobante.models import ComprobantePagoDistribucion, ComprobantePago
from decimal import Decimal

def fix_reserva_172():
    # Obtener la reserva
    reserva = Reserva.objects.get(id=172)
    print(f"\n=== Reserva {reserva.codigo} ===")
    print(f"cantidad_pasajeros: {reserva.cantidad_pasajeros}")
    print(f"pasajeros actuales: {reserva.pasajeros.count()}")

    # Mostrar pasajeros y sus pagos
    print("\n=== Pasajeros y pagos ===")
    for p in reserva.pasajeros.all():
        distribuciones = ComprobantePagoDistribucion.objects.filter(pasajero=p)
        total_pagado = sum([d.monto for d in distribuciones])
        print(f"{p.id}: {p.persona.nombre} {p.persona.apellido} - Pagos: {distribuciones.count()} - Total: ${total_pagado}")

    # Buscar el pasajero "Por Asignar 1" a eliminar
    pasajero_a_eliminar = Pasajero.objects.filter(
        reserva=reserva,
        persona__nombre="Por Asignar 1"
    ).first()

    if not pasajero_a_eliminar:
        print("\nNo se encontró el pasajero 'Por Asignar 1'")
        return

    print(f"\n=== Eliminando pasajero {pasajero_a_eliminar.id}: {pasajero_a_eliminar.persona.nombre} ===")

    # Obtener las distribuciones de pago de este pasajero
    distribuciones = ComprobantePagoDistribucion.objects.filter(pasajero=pasajero_a_eliminar)
    print(f"Distribuciones a eliminar: {distribuciones.count()}")

    for dist in distribuciones:
        print(f"  - {dist.comprobante.numero_comprobante}: ${dist.monto}")
        comprobante = dist.comprobante

        # Eliminar la distribución
        dist.delete()

        # Recalcular el monto total del comprobante
        distribuciones_restantes = ComprobantePagoDistribucion.objects.filter(comprobante=comprobante)
        nuevo_monto = sum([d.monto for d in distribuciones_restantes])
        print(f"    Nuevo monto del comprobante: ${nuevo_monto}")

        comprobante.monto = nuevo_monto
        comprobante.save()

    # Eliminar el pasajero
    pasajero_a_eliminar.delete()
    print(f"Pasajero {pasajero_a_eliminar.id} eliminado")

    # Actualizar el monto pagado de la reserva
    # Recalcular sumando todas las distribuciones
    todas_distribuciones = ComprobantePagoDistribucion.objects.filter(
        comprobante__reserva=reserva,
        comprobante__activo=True
    )
    monto_total_pagado = sum([d.monto for d in todas_distribuciones])
    reserva.monto_pagado = monto_total_pagado
    reserva.save()

    print(f"\n=== Resultado ===")
    reserva.refresh_from_db()
    print(f"cantidad_pasajeros: {reserva.cantidad_pasajeros}")
    print(f"pasajeros actuales: {reserva.pasajeros.count()}")
    print(f"monto_pagado: ${reserva.monto_pagado}")

    print("\n=== Pasajeros finales ===")
    for p in reserva.pasajeros.all():
        distribuciones = ComprobantePagoDistribucion.objects.filter(pasajero=p)
        total_pagado = sum([d.monto for d in distribuciones])
        print(f"{p.id}: {p.persona.nombre} {p.persona.apellido} - Total: ${total_pagado}")

if __name__ == "__main__":
    fix_reserva_172()
