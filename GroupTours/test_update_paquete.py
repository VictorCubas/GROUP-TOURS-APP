"""
Script para probar el UPDATE de paquetes de distribuidora
"""
import os
import django
import sys

# Fix encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.paquete.models import Paquete, SalidaPaquete, PrecioCatalogoHabitacion, PrecioCatalogoHotel
from decimal import Decimal

# Buscar el paquete que acabas de crear
paquete = Paquete.objects.filter(nombre='Rio Aereo Flexibble x2').first()

if not paquete:
    print("[ERROR] No se encontro el paquete 'Rio Aereo Flexibble x2'")
    exit(1)

print(f"[OK] Paquete encontrado: {paquete.nombre} (ID: {paquete.id})")
print(f"   Propio: {paquete.propio}")
print(f"   Distribuidora: {paquete.distribuidora.nombre if paquete.distribuidora else 'N/A'}")

# Buscar la salida
salida = paquete.salidas.first()

if not salida:
    print("[ERROR] No se encontro ninguna salida para este paquete")
    exit(1)

print(f"\n[OK] Salida encontrada: ID {salida.id}")
print(f"   Fecha salida: {salida.fecha_salida}")
print(f"   Fecha regreso: {salida.fecha_regreso}")
print(f"   Comision: {salida.comision}%")

# Verificar hoteles
hoteles = salida.hoteles.all()
print(f"\n[HOTELES] Hoteles asociados ({len(hoteles)}):")
for hotel in hoteles:
    print(f"   - {hotel.nombre} (ID: {hotel.id})")

# Verificar precios de catálogo POR HOTEL
precios_hotel = PrecioCatalogoHotel.objects.filter(salida=salida)
print(f"\n[PRECIOS HOTEL] Precios de catalogo POR HOTEL ({precios_hotel.count()}):")
for ph in precios_hotel:
    print(f"   - Hotel {ph.hotel.nombre}: ${ph.precio_catalogo}")

# Verificar precios de catálogo POR HABITACIÓN
precios_hab = PrecioCatalogoHabitacion.objects.filter(salida=salida)
print(f"\n[PRECIOS HABITACION] Precios de catalogo POR HABITACION ({precios_hab.count()}):")
for ph in precios_hab:
    print(f"   - Habitacion {ph.habitacion.id} ({ph.habitacion.tipo}) del hotel {ph.habitacion.hotel.nombre}: ${ph.precio_catalogo}")

# Verificar precio_actual y precio_final
print(f"\n[RESUMEN] Precios calculados:")
print(f"   precio_actual: ${salida.precio_actual}")
print(f"   precio_final: ${salida.precio_final}")
print(f"   precio_venta_sugerido_min: ${salida.precio_venta_sugerido_min}")
print(f"   precio_venta_sugerido_max: ${salida.precio_venta_sugerido_max}")

print("\n" + "="*60)
print("[OK] Diagnostico completo")
