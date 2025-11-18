"""
Script para eliminar las cotizaciones del día actual de la base de datos.
Útil para pruebas en el frontend.
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.moneda.models import CotizacionMoneda
from django.utils import timezone

def eliminar_cotizaciones_hoy():
    fecha_hoy = timezone.now().date()

    # Buscar cotizaciones del día
    cotizaciones_hoy = CotizacionMoneda.objects.filter(fecha_vigencia=fecha_hoy)

    cantidad = cotizaciones_hoy.count()

    if cantidad == 0:
        print(f"[OK] No hay cotizaciones para el dia {fecha_hoy.strftime('%d/%m/%Y')}")
        return

    print(f"[INFO] Cotizaciones encontradas para el dia {fecha_hoy.strftime('%d/%m/%Y')}:")
    for cotizacion in cotizaciones_hoy:
        print(f"  - {cotizacion.moneda.codigo}: {cotizacion.valor_en_guaranies} Gs")

    # Eliminar
    cotizaciones_hoy.delete()

    print(f"\n[OK] Eliminadas {cantidad} cotizacion(es) del dia {fecha_hoy.strftime('%d/%m/%Y')}")
    print("Ahora puedes probar el registro de cotizaciones desde el frontend.")

if __name__ == '__main__':
    eliminar_cotizaciones_hoy()
