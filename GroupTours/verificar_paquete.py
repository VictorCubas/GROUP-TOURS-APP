#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.paquete.models import Paquete, SalidaPaquete, PrecioCatalogoHotel, PrecioCatalogoHabitacion
from apps.hotel.models import Habitacion

# Buscar el paquete más reciente con "Rio de Janeiro"
p = Paquete.objects.filter(nombre__icontains='Rio de Janeiro').order_by('-fecha_creacion').first()

if not p:
    print("❌ No se encontró el paquete")
    exit(1)

print("=" * 70)
print("=== PAQUETE ===")
print("=" * 70)
print(f"ID: {p.id}")
print(f"Nombre: {p.nombre}")
print(f"Propio: {p.propio}")
print(f"Distribuidora: {p.distribuidora.nombre if p.distribuidora else 'N/A'}")
print(f"Moneda: {p.moneda.nombre if p.moneda else 'N/A'}")
print(f"Activo: {p.activo}")
print()

salida = p.salidas.first()
if not salida:
    print("❌ No se encontró ninguna salida")
    exit(1)

print("=" * 70)
print("=== SALIDA ===")
print("=" * 70)
print(f"ID: {salida.id}")
print(f"Fecha Salida: {salida.fecha_salida}")
print(f"Fecha Regreso: {salida.fecha_regreso}")
print(f"Seña: ${salida.senia}")
print(f"Comisión: {salida.comision}%")
print()

print("=" * 70)
print("=== HOTELES ASOCIADOS ===")
print("=" * 70)
for hotel in salida.hoteles.all():
    print(f"  - ID {hotel.id}: {hotel.nombre}")
print()

print("=" * 70)
print("=== PRECIOS DE CATÁLOGO POR HOTEL ===")
print("=" * 70)
precios_hotel = salida.precios_catalogo_hoteles.all()
if precios_hotel.exists():
    for pch in precios_hotel:
        print(f"  Hotel: {pch.hotel.nombre} (ID:{pch.hotel.id})")
        print(f"    Precio Catálogo: ${pch.precio_catalogo}")
        # Contar habitaciones de este hotel
        hab_count = Habitacion.objects.filter(hotel=pch.hotel, activo=True).count()
        print(f"    Habitaciones del hotel: {hab_count}")
        print()
else:
    print("  No hay precios de catálogo por hotel")
print()

print("=" * 70)
print("=== PRECIOS DE CATÁLOGO POR HABITACIÓN ===")
print("=" * 70)
precios_hab = salida.precios_catalogo.all().order_by('habitacion__hotel__id', 'habitacion__id')
total_precios_hab = precios_hab.count()
print(f"Total de registros: {total_precios_hab}")
print()

# Agrupar por hotel
from collections import defaultdict
por_hotel = defaultdict(list)
for pc in precios_hab:
    por_hotel[pc.habitacion.hotel.id].append(pc)

for hotel_id, precios in sorted(por_hotel.items()):
    hotel_nombre = precios[0].habitacion.hotel.nombre
    print(f"  Hotel: {hotel_nombre} (ID:{hotel_id}) - {len(precios)} habitaciones")
    for pc in precios[:5]:  # Mostrar solo las primeras 5
        print(f"    - Hab ID:{pc.habitacion.id} ({pc.habitacion.tipo_habitacion.nombre}): ${pc.precio_catalogo}")
    if len(precios) > 5:
        print(f"    ... y {len(precios) - 5} habitaciones más")
    print()

print("=" * 70)
print("=== CÁLCULOS DE PRECIOS ===")
print("=" * 70)
print(f"precio_actual (mínimo): ${salida.precio_actual}")
print(f"precio_final (máximo): ${salida.precio_final}")
print()
print(f"precio_venta_sugerido_min: ${salida.precio_venta_sugerido_min}")
print(f"precio_venta_sugerido_max: ${salida.precio_venta_sugerido_max}")
print()

# Verificar cálculos
print("=" * 70)
print("=== VERIFICACIÓN DE CÁLCULOS ===")
print("=" * 70)

# Obtener todos los precios
todos_precios = [pc.precio_catalogo for pc in precios_hab]
if todos_precios:
    min_precio = min(todos_precios)
    max_precio = max(todos_precios)

    print(f"✓ Precio mínimo en BD: ${min_precio}")
    print(f"✓ Precio máximo en BD: ${max_precio}")
    print()

    # Verificar si coinciden
    if salida.precio_actual == min_precio:
        print(f"✅ precio_actual CORRECTO: ${salida.precio_actual} = ${min_precio}")
    else:
        print(f"❌ precio_actual INCORRECTO: ${salida.precio_actual} ≠ ${min_precio}")

    if salida.precio_final == max_precio:
        print(f"✅ precio_final CORRECTO: ${salida.precio_final} = ${max_precio}")
    else:
        print(f"❌ precio_final INCORRECTO: ${salida.precio_final} ≠ ${max_precio}")
    print()

    # Verificar precio de venta (con comisión)
    from decimal import Decimal
    comision_decimal = Decimal(str(salida.comision))
    factor = Decimal("1") + (comision_decimal / Decimal("100"))

    precio_venta_min_esperado = min_precio * factor
    precio_venta_max_esperado = max_precio * factor

    print(f"✓ Precio venta mínimo esperado: ${min_precio} × {factor} = ${precio_venta_min_esperado}")
    print(f"✓ Precio venta máximo esperado: ${max_precio} × {factor} = ${precio_venta_max_esperado}")
    print()

    if salida.precio_venta_sugerido_min == precio_venta_min_esperado:
        print(f"✅ precio_venta_sugerido_min CORRECTO: ${salida.precio_venta_sugerido_min}")
    else:
        print(f"❌ precio_venta_sugerido_min INCORRECTO")
        print(f"   Actual: ${salida.precio_venta_sugerido_min}")
        print(f"   Esperado: ${precio_venta_min_esperado}")

    if salida.precio_venta_sugerido_max == precio_venta_max_esperado:
        print(f"✅ precio_venta_sugerido_max CORRECTO: ${salida.precio_venta_sugerido_max}")
    else:
        print(f"❌ precio_venta_sugerido_max INCORRECTO")
        print(f"   Actual: ${salida.precio_venta_sugerido_max}")
        print(f"   Esperado: ${precio_venta_max_esperado}")

print()
print("=" * 70)
print("=== FIN DE LA VERIFICACIÓN ===")
print("=" * 70)
