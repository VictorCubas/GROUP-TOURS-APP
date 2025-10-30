"""
Script para actualizar pasajeros existentes con _PEND en el documento
y marcarlos con por_asignar=True

Ejecutar con:
python actualizar_pasajeros_pendientes.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Pasajero

def actualizar_pasajeros_pendientes():
    """
    Busca todos los pasajeros con _PEND en el documento
    y los marca con por_asignar=True
    """
    print("Buscando pasajeros pendientes...")

    # Buscar pasajeros con _PEND en el documento
    pasajeros_pendientes = Pasajero.objects.filter(
        persona__documento__contains='_PEND',
        por_asignar=False  # Solo los que aún no están marcados
    )

    total = pasajeros_pendientes.count()
    print(f"Encontrados {total} pasajeros pendientes sin marcar")

    if total == 0:
        print("[OK] No hay pasajeros para actualizar")
        return

    # Actualizar todos
    actualizados = pasajeros_pendientes.update(por_asignar=True)

    print(f"[OK] {actualizados} pasajeros actualizados correctamente")

    # Mostrar algunos ejemplos
    print("\nEjemplos de pasajeros actualizados:")
    for pasajero in Pasajero.objects.filter(por_asignar=True)[:5]:
        print(f"  - ID: {pasajero.id} | Documento: {pasajero.persona.documento} | Reserva: {pasajero.reserva.codigo}")

if __name__ == '__main__':
    try:
        actualizar_pasajeros_pendientes()
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
