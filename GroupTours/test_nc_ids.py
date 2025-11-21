"""
Script para verificar los campos de ID de notas de credito.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva
from apps.reserva.serializers import ReservaDetalleSerializer

# Buscar reservas con NCs generadas
reservas = Reserva.objects.filter(
    activo=True,
    cantidad_pasajeros__gt=0
).order_by('-id')[:3]

print(f"\nVerificando {reservas.count()} reservas con pasajeros")

for reserva in reservas:
    print(f"\n{'='*70}")
    print(f"RESERVA #{reserva.id} - {reserva.codigo}")
    print(f"Modalidad: {reserva.get_modalidad_facturacion_display() or 'No definida'}")

    # Serializar
    serializer = ReservaDetalleSerializer(reserva)
    data = serializer.data

    # Mostrar campos de NC global
    print(f"\n[NC GLOBAL]")
    print(f"  factura_global_generada: {data.get('factura_global_generada')}")
    print(f"  factura_global_id: {data.get('factura_global_id')}")
    print(f"  nota_credito_global_ya_generada: {data.get('nota_credito_global_ya_generada')}")
    print(f"  nota_credito_global_id: {data.get('nota_credito_global_id')}")

    # Verificar que si tiene NC generada, tambien tiene ID
    if data.get('nota_credito_global_ya_generada'):
        if data.get('nota_credito_global_id'):
            print(f"  [OK] Tiene NC global generada Y tiene ID")
        else:
            print(f"  [ERROR] Tiene NC generada pero falta el ID!")

    # Mostrar pasajeros con NC individual
    pasajeros = data.get('pasajeros', [])
    pasajeros_con_nc = [p for p in pasajeros if p.get('nota_credito_individual_ya_generada')]

    if pasajeros_con_nc:
        print(f"\n[NC INDIVIDUALES] ({len(pasajeros_con_nc)} pasajeros con NC)")
        for pas in pasajeros_con_nc:
            persona_info = pas.get('persona', {})
            nombre = persona_info.get('nombre_completo', 'Sin nombre')
            print(f"  Pasajero ID {pas.get('id')}: {nombre}")
            print(f"    - factura_individual_generada: {pas.get('factura_individual_generada')}")
            print(f"    - factura_id: {pas.get('factura_id')}")
            print(f"    - nota_credito_individual_ya_generada: {pas.get('nota_credito_individual_ya_generada')}")
            print(f"    - nota_credito_individual_id: {pas.get('nota_credito_individual_id')}")

            # Verificar consistencia
            if pas.get('nota_credito_individual_ya_generada'):
                if pas.get('nota_credito_individual_id'):
                    print(f"    [OK] Tiene NC individual generada Y tiene ID")
                else:
                    print(f"    [ERROR] Tiene NC generada pero falta el ID!")

print(f"\n{'='*70}")
print("[OK] Verificacion completada!")
