#!/usr/bin/env python
"""Script para actualizar el número de factura 49 al formato correcto con PE 003"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica

print("=" * 80)
print("ACTUALIZANDO NUMERO DE FACTURA 49")
print("=" * 80)

try:
    # Obtener la factura 49
    factura = FacturaElectronica.objects.get(id=49)

    print(f"\nFactura actual:")
    print(f"  - ID: {factura.id}")
    print(f"  - Numero actual: {factura.numero_factura}")
    print(f"  - PE: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

    # Obtener las partes del número actual
    partes = factura.numero_factura.split('-')

    if len(partes) != 3:
        print(f"\nERROR: Formato de numero de factura inesperado: {factura.numero_factura}")
        sys.exit(1)

    establecimiento = partes[0]  # 001
    punto_expedicion_viejo = partes[1]  # 001
    numero_secuencial = partes[2]  # 0000046

    # Construir el nuevo número con PE 003
    nuevo_numero = f"{establecimiento}-003-{numero_secuencial}"

    print(f"\nActualizando numero de factura:")
    print(f"  - Numero anterior: {factura.numero_factura}")
    print(f"  - Numero nuevo:    {nuevo_numero}")

    # Verificar que no exista otra factura con ese número
    factura_existente = FacturaElectronica.objects.filter(
        numero_factura=nuevo_numero
    ).exclude(id=factura.id).first()

    if factura_existente:
        print(f"\nADVERTENCIA: Ya existe una factura con el numero {nuevo_numero}")
        print(f"  - Factura ID: {factura_existente.id}")
        print("\nNO se realizara el cambio para evitar duplicados")
        sys.exit(1)

    # Actualizar el número
    factura.numero_factura = nuevo_numero
    factura.save(update_fields=['numero_factura'])

    print("\n*** NUMERO DE FACTURA ACTUALIZADO EXITOSAMENTE ***")

    # Verificar
    factura.refresh_from_db()
    print(f"\nVerificacion:")
    print(f"  - Factura {factura.id}")
    print(f"  - Numero: {factura.numero_factura}")
    print(f"  - PE: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

    print("\nAhora la nota de credito mostrara el numero correcto: 001-003-0000046")

except FacturaElectronica.DoesNotExist:
    print("\nERROR: Factura 49 no existe")
    sys.exit(1)
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
