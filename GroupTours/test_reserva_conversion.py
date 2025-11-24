#!/usr/bin/env python
"""
Script de prueba para verificar la conversión de monedas en reservas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva
from apps.paquete.models import SalidaPaquete, Paquete
from apps.hotel.models import Habitacion
from apps.persona.models import PersonaFisica
from decimal import Decimal

print("="*70)
print("PRUEBA DE CONVERSIÓN DE MONEDAS EN RESERVAS")
print("="*70)

# Datos de la prueba
paquete_id = 157
salida_id = 272
habitacion_id = 64  # Habitación single, $60 USD/noche
titular_id = 15

# Obtener instancias
paquete = Paquete.objects.get(id=paquete_id)
salida = SalidaPaquete.objects.get(id=salida_id)
habitacion = Habitacion.objects.get(id=habitacion_id)
titular = PersonaFisica.objects.get(id=titular_id)

print(f"\n📦 DATOS DEL PAQUETE:")
print(f"   ID: {paquete.id}")
print(f"   Nombre: {paquete.nombre}")
print(f"   Moneda: {paquete.moneda.codigo} ({paquete.moneda.simbolo})")
print(f"   Tipo: {'Propio' if paquete.propio else 'Distribuidora'}")

print(f"\n🏨 DATOS DE LA HABITACIÓN:")
print(f"   ID: {habitacion.id}")
print(f"   Número: {habitacion.numero}")
print(f"   Tipo: {habitacion.tipo}")
print(f"   Precio/noche: {habitacion.precio_noche} {habitacion.moneda.codigo}")

print(f"\n✈️ DATOS DE LA SALIDA:")
print(f"   ID: {salida.id}")
print(f"   Fecha salida: {salida.fecha_salida}")
print(f"   Fecha regreso: {salida.fecha_regreso}")
print(f"   Noches: {(salida.fecha_regreso - salida.fecha_salida).days}")
print(f"   Ganancia: {salida.ganancia}%")

# Crear reserva de prueba
print(f"\n🎫 CREANDO RESERVA...")
reserva = Reserva.objects.create(
    paquete=paquete,
    salida=salida,
    habitacion=habitacion,
    titular=titular,
    cantidad_pasajeros=habitacion.capacidad,
    activo=True,
    monto_pagado=0
)

# Calcular precio
precio_unitario = reserva.calcular_precio_unitario()
reserva.precio_unitario = precio_unitario
reserva.save()

print(f"   ✓ Reserva creada: {reserva.codigo}")

print(f"\n💰 CÁLCULO DETALLADO:")
print(f"   Precio noche habitación: ${habitacion.precio_noche} USD")
print(f"   Noches: 7")
print(f"   Cotización USD->PYG: 7,110")
print(f"   Servicios del paquete: 160 ₲")
print(f"   Ganancia: 30%")
print(f"")
print(f"   Fórmula:")
print(f"   1. Precio habitación: $60 × 7 = $420 USD")
print(f"   2. Convertir a PYG: $420 × 7,110 = 2,986,200 ₲")
print(f"   3. Sumar servicios: 2,986,200 + 160 = 2,986,360 ₲")
print(f"   4. Aplicar ganancia 30%: 2,986,360 × 1.3 = 3,882,268 ₲")

print(f"\n📊 RESULTADOS:")
precio_esperado = Decimal("3882268")
precio_obtenido = precio_unitario

print(f"   Precio esperado: {precio_esperado:,.2f} ₲")
print(f"   Precio obtenido: {precio_obtenido:,.2f} ₲")
print(f"   Diferencia: {abs(precio_obtenido - precio_esperado):,.2f} ₲")

if precio_obtenido == precio_esperado:
    print(f"\n   ✅ ¡CORRECTO! Los precios coinciden perfectamente.")
else:
    print(f"\n   ❌ ERROR: Los precios no coinciden.")
    print(f"   Error: {((precio_obtenido - precio_esperado) / precio_esperado * 100):.2f}%")

print(f"\n📋 DATOS DE LA RESERVA CREADA:")
print(f"   ID: {reserva.id}")
print(f"   Código: {reserva.codigo}")
print(f"   Estado: {reserva.estado}")
print(f"   Cantidad pasajeros: {reserva.cantidad_pasajeros}")
print(f"   Precio unitario: {reserva.precio_unitario:,.2f}")
print(f"   Costo total: {reserva.costo_total_estimado:,.2f}")

# Comparar con precio_venta_sugerido_min de la salida
print(f"\n🔍 VERIFICACIÓN CON SALIDA:")
print(f"   precio_venta_sugerido_min: {salida.precio_venta_sugerido_min:,.2f} ₲")
print(f"   Coincide con reserva: {'✅ SÍ' if precio_obtenido == salida.precio_venta_sugerido_min else '❌ NO'}")

print("\n" + "="*70)
print("PRUEBA COMPLETADA")
print("="*70)

