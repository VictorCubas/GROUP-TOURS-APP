"""
Script para limpiar movimientos de caja duplicados.

Este script identifica y elimina movimientos de caja duplicados que se crearon
debido a la doble ejecución (modelo save() + signal post_save).

Ejecutar con:
    python limpiar_movimientos_duplicados.py
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.arqueo_caja.models import MovimientoCaja
from apps.comprobante.models import ComprobantePago
from django.db.models import Count


def limpiar_movimientos_duplicados():
    """
    Limpia los movimientos duplicados manteniendo el más reciente de cada comprobante.
    """
    print("=" * 80)
    print("LIMPIEZA DE MOVIMIENTOS DUPLICADOS")
    print("=" * 80)
    print()

    # Encontrar comprobantes con múltiples movimientos activos
    comprobantes_con_duplicados = (
        MovimientoCaja.objects
        .filter(activo=True, comprobante__isnull=False)
        .values('comprobante')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    total_comprobantes_afectados = comprobantes_con_duplicados.count()

    if total_comprobantes_afectados == 0:
        print("✅ No se encontraron movimientos duplicados.")
        return

    print(f"⚠️  Encontrados {total_comprobantes_afectados} comprobantes con movimientos duplicados.")
    print()

    movimientos_eliminados = 0

    for item in comprobantes_con_duplicados:
        comprobante_id = item['comprobante']
        total_movimientos = item['total']

        try:
            comprobante = ComprobantePago.objects.get(id=comprobante_id)
        except ComprobantePago.DoesNotExist:
            print(f"⚠️  Comprobante ID {comprobante_id} no existe. Omitiendo...")
            continue

        # Obtener todos los movimientos de este comprobante (ordenados por fecha, más reciente primero)
        movimientos = MovimientoCaja.objects.filter(
            comprobante=comprobante,
            activo=True
        ).order_by('-fecha_hora_movimiento')

        print(f"Comprobante {comprobante.numero_comprobante}:")
        print(f"  - Movimientos encontrados: {total_movimientos}")

        # Mantener el primer movimiento (más reciente), eliminar el resto
        movimientos_a_eliminar = list(movimientos[1:])

        for mov in movimientos_a_eliminar:
            print(f"  - Eliminando movimiento duplicado: {mov.numero_movimiento}")
            print(f"    Usuario: {mov.usuario_nombre}")
            print(f"    Fecha: {mov.fecha_hora_movimiento}")
            print(f"    Monto: ${mov.monto}")

            # Marcar como inactivo en lugar de eliminar (para auditoría)
            mov.activo = False
            mov.descripcion = f"[DUPLICADO ELIMINADO] {mov.descripcion or ''}"
            mov.save()
            movimientos_eliminados += 1

        if movimientos.exists():
            mov_mantenido = movimientos.first()
            print(f"  ✅ Mantenido movimiento: {mov_mantenido.numero_movimiento}")
            print(f"    Usuario: {mov_mantenido.usuario_nombre}")
            print(f"    Fecha: {mov_mantenido.fecha_hora_movimiento}")
        print()

    print("=" * 80)
    print(f"✅ Limpieza completada.")
    print(f"   - Comprobantes procesados: {total_comprobantes_afectados}")
    print(f"   - Movimientos duplicados marcados como inactivos: {movimientos_eliminados}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        limpiar_movimientos_duplicados()
    except Exception as e:
        print(f"❌ Error durante la limpieza: {str(e)}")
        import traceback
        traceback.print_exc()
