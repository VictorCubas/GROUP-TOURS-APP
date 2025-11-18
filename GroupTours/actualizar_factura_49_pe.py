#!/usr/bin/env python
"""Script para actualizar el punto de expedición de la factura 49 a PE 003"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica, PuntoExpedicion

print("=" * 80)
print("ACTUALIZANDO PUNTO DE EXPEDICION - FACTURA 49")
print("=" * 80)

try:
    # Obtener la factura 49
    factura = FacturaElectronica.objects.get(id=49)
    print(f"\nFactura encontrada:")
    print(f"  - ID: {factura.id}")
    print(f"  - Numero: {factura.numero_factura}")
    print(f"  - PE actual: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

    # Obtener el PE 003 del establecimiento 001
    pe_003 = PuntoExpedicion.objects.filter(
        codigo='003',
        establecimiento__codigo='001'
    ).first()

    if not pe_003:
        print("\nERROR: No se encontro el Punto de Expedicion 003 del Establecimiento 001")
        sys.exit(1)

    print(f"\nPunto de Expedicion 003:")
    print(f"  - {pe_003}")
    print(f"  - Establecimiento: {pe_003.establecimiento}")

    # Actualizar el punto de expedición
    print(f"\nActualizando...")
    print(f"  PE Anterior: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")
    print(f"  PE Nuevo:    {pe_003} (codigo: {pe_003.codigo})")

    factura.punto_expedicion = pe_003
    factura.save(update_fields=['punto_expedicion'])

    print("\n*** FACTURA ACTUALIZADA EXITOSAMENTE ***")

    # Verificar el cambio
    factura.refresh_from_db()
    print(f"\nVerificacion:")
    print(f"  - Factura {factura.id}")
    print(f"  - Numero: {factura.numero_factura}")
    print(f"  - PE actual: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

    print("\nAhora puedes generar la nota de credito desde la Caja 5 (PE 003)")

except FacturaElectronica.DoesNotExist:
    print("\nERROR: Factura 49 no existe")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
