#!/usr/bin/env python
"""Script para corregir el punto de expedición de la factura 49"""

import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica, PuntoExpedicion

print("=" * 80)
print("CORRECCION DE PUNTO DE EXPEDICION - FACTURA 49")
print("=" * 80)

# Obtener la factura 49
try:
    factura = FacturaElectronica.objects.get(id=49)
    print(f"\nFactura encontrada:")
    print(f"  - ID: {factura.id}")
    print(f"  - Numero: {factura.numero_factura}")
    print(f"  - PE actual: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

    # Obtener el PE 003
    pe_003 = PuntoExpedicion.objects.filter(codigo='003').first()

    if not pe_003:
        print("\nERROR: No se encontro el Punto de Expedicion 003")
        sys.exit(1)

    print(f"\nPunto de Expedicion 003:")
    print(f"  - {pe_003}")
    print(f"  - Establecimiento: {pe_003.establecimiento}")

    # Confirmar el cambio
    print(f"\n{'='*80}")
    print("SE VA A REALIZAR EL SIGUIENTE CAMBIO:")
    print(f"  PE Actual:  {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")
    print(f"  PE Nuevo:   {pe_003} (codigo: {pe_003.codigo})")
    print(f"{'='*80}")

    respuesta = input("\nDesea continuar? (s/n): ")

    if respuesta.lower() == 's':
        # Actualizar el punto de expedición
        factura.punto_expedicion = pe_003
        factura.save(update_fields=['punto_expedicion'])

        print("\n*** FACTURA ACTUALIZADA EXITOSAMENTE ***")

        # Verificar el cambio
        factura.refresh_from_db()
        print(f"\nVerificacion:")
        print(f"  - PE actual: {factura.punto_expedicion} (codigo: {factura.punto_expedicion.codigo})")

        # Nota: El número de factura no cambia automáticamente
        print(f"\nNOTA: El numero de factura sigue siendo '{factura.numero_factura}'")
        print("      Si necesitas que el numero refleje el nuevo PE (001-003-XXXXXX),")
        print("      debes actualizarlo manualmente o regenerar la factura.")

    else:
        print("\nOperacion cancelada")

except FacturaElectronica.DoesNotExist:
    print("\nERROR: Factura 49 no existe")
except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
