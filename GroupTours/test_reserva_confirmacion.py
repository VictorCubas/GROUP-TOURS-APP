"""
Script de prueba para verificar la nueva lógica de confirmación de reservas.

Este script simula el flujo:
1. Crear una reserva con titular_id y monto_pagado
2. Verificar que el estado sea "confirmada" si se pagó la seña
3. Verificar que datos_completos = False porque falta cargar pasajeros
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva, Pasajero
from apps.paquete.models import Paquete, SalidaPaquete
from apps.hotel.models import Habitacion
from apps.persona.models import PersonaFisica
from decimal import Decimal

def test_reserva_con_sena():
    """
    Simula la creación de una reserva con seña pagada pero sin pasajeros completos
    """
    print("=" * 80)
    print("TEST: Creación de reserva con seña pagada")
    print("=" * 80)

    # Obtener datos de ejemplo (ajusta los IDs según tu base de datos)
    try:
        paquete = Paquete.objects.get(id=138)
        salida = SalidaPaquete.objects.get(id=246)
        habitacion = Habitacion.objects.get(id=12)
        titular = PersonaFisica.objects.get(id=15)
    except Exception as e:
        print(f"ERROR: Error obteniendo datos: {e}")
        print("\nIntentando con cualquier dato disponible...")

        paquete = Paquete.objects.first()
        salida = SalidaPaquete.objects.first()
        habitacion = Habitacion.objects.first()
        titular = PersonaFisica.objects.first()

        if not all([paquete, salida, habitacion, titular]):
            print("ERROR: No hay datos suficientes en la base de datos para hacer la prueba")
            return

    print(f"\nPaquete: {paquete.nombre}")
    print(f"Salida: {salida.fecha_salida} - {salida.fecha_regreso}")
    print(f"Habitacion: {habitacion.numero} (Capacidad: {habitacion.capacidad})")
    print(f"Titular: {titular.nombre} {titular.apellido}")

    # Crear la reserva
    print("\n" + "-" * 80)
    print("Creando reserva...")
    print("-" * 80)

    reserva = Reserva.objects.create(
        paquete=paquete,
        salida=salida,
        habitacion=habitacion,
        titular=titular,
        monto_pagado=Decimal("440")
    )

    # Actualizar el estado de la reserva (normalmente lo hace el serializer)
    reserva.actualizar_estado()

    print(f"\nReserva creada: {reserva.codigo}")
    print(f"   - Cantidad de pasajeros: {reserva.cantidad_pasajeros}")
    print(f"   - Precio unitario: {reserva.precio_unitario}")
    print(f"   - Sena total requerida: {reserva.seña_total}")
    print(f"   - Monto pagado: {reserva.monto_pagado}")
    print(f"   - Costo total estimado: {reserva.costo_total_estimado}")

    # Verificar pasajeros creados automáticamente
    pasajeros = reserva.pasajeros.all()
    print(f"\nPasajeros creados automaticamente: {pasajeros.count()}")
    for p in pasajeros:
        print(f"   - {p.persona.nombre} {p.persona.apellido} (Titular: {p.es_titular})")

    # Verificar flags
    print(f"\nFlags de la reserva:")
    print(f"   - datos_completos: {reserva.datos_completos}")
    print(f"   - faltan_datos_pasajeros: {reserva.faltan_datos_pasajeros}")
    print(f"   - pasajeros_cargados: {reserva.pasajeros_cargados}/{reserva.cantidad_pasajeros}")

    # Verificar condiciones de confirmación
    print(f"\nVerificaciones:")
    print(f"   - puede_confirmarse(): {reserva.puede_confirmarse()}")
    print(f"   - esta_totalmente_pagada(): {reserva.esta_totalmente_pagada()}")
    print(f"   - Estado actual: {reserva.estado}")
    print(f"   - Estado display: {reserva.estado_display}")

    # Calcular si debería estar confirmada
    deberia_estar_confirmada = reserva.monto_pagado >= reserva.seña_total

    print(f"\n" + "=" * 80)
    if reserva.estado == "confirmada" and deberia_estar_confirmada:
        print("EXITO: La reserva quedo CONFIRMADA como se esperaba")
        print(f"   Razon: Se pago la sena total ({reserva.monto_pagado} >= {reserva.seña_total})")
        print(f"   Los datos de pasajeros NO estan completos ({reserva.pasajeros_cargados}/{reserva.cantidad_pasajeros})")
    elif reserva.estado == "pendiente" and not deberia_estar_confirmada:
        print("EXITO: La reserva quedo PENDIENTE como se esperaba")
        print(f"   Razon: NO se pago la sena completa ({reserva.monto_pagado} < {reserva.seña_total})")
    else:
        print("ERROR: El estado no es el esperado")
        print(f"   Estado actual: {reserva.estado}")
        print(f"   Deberia ser: {'confirmada' if deberia_estar_confirmada else 'pendiente'}")
    print("=" * 80)

    # Limpiar (opcional - comentar si quieres mantener la reserva)
    print(f"\nReserva creada con ID: {reserva.id}")
    print("Nota: La reserva no se eliminara automaticamente para que puedas verificarla")

if __name__ == "__main__":
    test_reserva_con_sena()
