#!/usr/bin/env python
"""Script para ver qué caja está asociada al PE 001"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import PuntoExpedicion
from apps.arqueo_caja.models import Caja

print("=" * 60)
print("CAJAS POR PUNTO DE EXPEDICION")
print("=" * 60)

# Buscar PE 001
pe_001 = PuntoExpedicion.objects.filter(codigo='001').first()

if pe_001:
    print(f"\nPunto Expedicion 001: {pe_001}")
    print(f"  - Establecimiento: {pe_001.establecimiento}")

    # Buscar caja asociada
    try:
        caja = Caja.objects.get(punto_expedicion=pe_001)
        print(f"\nCaja asociada al PE 001:")
        print(f"  - ID: {caja.id}")
        print(f"  - Nombre: {caja.nombre}")
        print(f"  - Estado: {caja.estado_actual}")
        print(f"  - Activa: {caja.activo}")
    except Caja.DoesNotExist:
        print("\n  NO HAY CAJA ASOCIADA AL PE 001")
else:
    print("\nNo se encontro el PE 001")

print("\n" + "=" * 60)
print("TODAS LAS CAJAS Y SUS PUNTOS DE EXPEDICION:")
print("=" * 60)

cajas = Caja.objects.filter(activo=True)
for caja in cajas:
    print(f"\nCaja {caja.id}: {caja.nombre}")
    print(f"  - Numero: {caja.numero_caja}")
    print(f"  - PE: {caja.punto_expedicion.codigo if caja.punto_expedicion else 'N/A'}")
    print(f"  - Estado: {caja.estado_actual}")
