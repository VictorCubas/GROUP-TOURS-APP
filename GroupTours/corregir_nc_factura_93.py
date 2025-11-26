#!/usr/bin/env python
"""
Script para corregir la NC emitida en factura 93.
Cancela la reserva asociada y libera cupos si aún no se hizo.

Uso:
    python corregir_nc_factura_93.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica, NotaCreditoElectronica
from apps.reserva.models import Reserva


def corregir_nc_factura_93():
    """
    Corrige la NC emitida en factura 93:
    - Verifica si la reserva está cancelada
    - Si no lo está, la cancela
    - Libera cupos del paquete
    """
    
    print("=" * 80)
    print("CORRECCIÓN DE NC - FACTURA 93")
    print("=" * 80)
    
    try:
        # 1. Buscar la factura 93
        print("\n1. Buscando factura 93...")
        factura = FacturaElectronica.objects.get(id=93, es_configuracion=False)
        print(f"   ✅ Factura encontrada: {factura.numero_factura}")
        print(f"      Cliente: {factura.cliente_nombre}")
        print(f"      Total: Gs. {factura.total_general:,.0f}")
        
        # 2. Verificar si tiene reserva asociada
        print("\n2. Verificando reserva asociada...")
        if not factura.reserva:
            print("   ⚠️  Esta factura NO tiene reserva asociada")
            print("   No hay nada que corregir.")
            return
        
        reserva = factura.reserva
        print(f"   ✅ Reserva encontrada: {reserva.codigo}")
        print(f"      Estado actual: {reserva.estado}")
        print(f"      Paquete: {reserva.paquete.nombre if reserva.paquete else 'N/A'}")
        print(f"      Cantidad pasajeros: {reserva.cantidad_pasajeros}")
        
        # 3. Verificar notas de crédito emitidas
        print("\n3. Verificando notas de crédito...")
        notas_credito = factura.notas_credito.filter(activo=True)
        if notas_credito.exists():
            print(f"   📄 Se encontraron {notas_credito.count()} NC(s):")
            for nc in notas_credito:
                print(f"      - {nc.numero_nota_credito}: Gs. {nc.total_general:,.0f} (Motivo: {nc.get_motivo_display()})")
        else:
            print("   ⚠️  No se encontraron NCs para esta factura")
        
        # 4. Verificar si la reserva está cancelada
        print("\n4. Verificando estado de la reserva...")
        if reserva.estado == 'cancelada':
            print("   ℹ️  La reserva YA está cancelada")
            print(f"      Fecha cancelación: {reserva.fecha_cancelacion}")
            print(f"      Motivo: {reserva.motivo_cancelacion}")
            print("\n   ✅ No se requiere acción. Todo está correcto.")
            return
        
        # 5. Cancelar la reserva
        print("\n5. Cancelando la reserva...")
        print(f"   Estado actual: {reserva.estado}")
        print("   Aplicando cancelación...")
        
        exito = reserva.marcar_cancelada(
            motivo_cancelacion_id='2',  # Cambio de planes del cliente
            motivo_observaciones=(
                f"Cancelada manualmente - Corrección de NC automática.\n"
                f"Factura: {factura.numero_factura}\n"
                f"NC emitida con motivo 2 (Devolución) no canceló automáticamente por bug.\n"
                f"Corrección aplicada con script."
            ),
            liberar_cupo=True
        )
        
        if exito:
            print("   ✅ Reserva cancelada exitosamente")
            print(f"      Nuevo estado: {reserva.estado}")
            print(f"      Cupos liberados: {reserva.cupos_liberados}")
            print(f"      Fecha cancelación: {reserva.fecha_cancelacion}")
        else:
            print("   ⚠️  No se pudo cancelar la reserva")
        
        # 6. Resumen final
        print("\n" + "=" * 80)
        print("RESUMEN DE LA CORRECCIÓN")
        print("=" * 80)
        print(f"Factura:         {factura.numero_factura}")
        print(f"Reserva:         {reserva.codigo}")
        print(f"Estado final:    {reserva.estado}")
        print(f"Cupos liberados: {'Sí' if reserva.cupos_liberados else 'No'}")
        
        if notas_credito.exists():
            total_nc = sum(nc.total_general for nc in notas_credito)
            print(f"Total NC:        Gs. {total_nc:,.0f}")
        
        print("=" * 80)
        print("✅ CORRECCIÓN COMPLETADA")
        print("=" * 80)
        
    except FacturaElectronica.DoesNotExist:
        print("   ❌ ERROR: Factura 93 no encontrada")
        print("   Verifica que el ID sea correcto.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    corregir_nc_factura_93()

