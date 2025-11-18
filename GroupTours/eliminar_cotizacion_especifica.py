"""
Script para eliminar la cotización del 16/11/2025.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.moneda.models import CotizacionMoneda, Moneda
from datetime import date

def eliminar_cotizacion_16_nov():
    fecha_ayer = date(2025, 11, 16)

    try:
        moneda_usd = Moneda.objects.get(codigo='USD')

        # Buscar cotización del 16/11/2025
        cotizacion = CotizacionMoneda.objects.filter(
            moneda=moneda_usd,
            fecha_vigencia=fecha_ayer
        ).first()

        if cotizacion:
            print(f"[INFO] Encontrada cotizacion: {cotizacion}")
            print(f"       Fecha: {cotizacion.fecha_vigencia}")
            print(f"       Valor: {cotizacion.valor_en_guaranies} Gs")

            cotizacion.delete()
            print(f"\n[OK] Cotizacion del {fecha_ayer.strftime('%d/%m/%Y')} eliminada exitosamente")
        else:
            print(f"[INFO] No se encontro cotizacion para el {fecha_ayer.strftime('%d/%m/%Y')}")

    except Moneda.DoesNotExist:
        print("[ERROR] No existe la moneda USD en la base de datos")

if __name__ == '__main__':
    eliminar_cotizacion_16_nov()
