"""
Script para corregir el movimiento de caja con monto 0 de la NC 001-003-0000005
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.arqueo_caja.models import MovimientoCaja
from apps.facturacion.models import NotaCreditoElectronica

def corregir_movimiento_nc():
    """
    Busca el movimiento de caja con monto 0 para la NC 001-003-0000005
    y lo actualiza con el monto correcto de la nota de crédito.
    """
    # Buscar la nota de crédito
    try:
        nc = NotaCreditoElectronica.objects.get(numero_nota_credito='001-003-0000005')
        print(f"[OK] Nota de Credito encontrada: {nc.numero_nota_credito}")
        print(f"   Total general: Gs. {nc.total_general:,.0f}")
    except NotaCreditoElectronica.DoesNotExist:
        print("[ERROR] No se encontro la NC 001-003-0000005")
        return

    # Buscar el movimiento con monto 0
    try:
        movimiento = MovimientoCaja.objects.get(
            referencia=f"NC: {nc.numero_nota_credito}",
            activo=True
        )
        print(f"\n[OK] Movimiento encontrado: {movimiento.numero_movimiento}")
        print(f"   Monto actual: Gs. {movimiento.monto:,.0f}")

        # Actualizar el monto
        movimiento.monto = nc.total_general
        movimiento.save()

        print(f"\n[OK] Movimiento actualizado correctamente")
        print(f"   Nuevo monto: Gs. {movimiento.monto:,.0f}")

    except MovimientoCaja.DoesNotExist:
        print(f"[ERROR] No se encontro movimiento para NC: {nc.numero_nota_credito}")
    except MovimientoCaja.MultipleObjectsReturned:
        print(f"[WARN] Se encontraron multiples movimientos para NC: {nc.numero_nota_credito}")
        movimientos = MovimientoCaja.objects.filter(
            referencia=f"NC: {nc.numero_nota_credito}",
            activo=True
        )
        for mov in movimientos:
            print(f"   - {mov.numero_movimiento}: Gs. {mov.monto:,.0f}")

if __name__ == '__main__':
    print("=" * 60)
    print("Correccion de movimiento de caja con monto 0")
    print("=" * 60)
    corregir_movimiento_nc()
    print("\n" + "=" * 60)
