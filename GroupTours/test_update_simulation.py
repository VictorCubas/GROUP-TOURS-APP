"""
Simular el procesamiento del UPDATE con el payload proporcionado
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Datos del payload
precios_catalogo_data = [
    { 'habitacion_id': 1, 'precio_catalogo': 1000 },
    { 'habitacion_id': 2, 'precio_catalogo': 1240 },
    { 'habitacion_id': 3, 'precio_catalogo': 1500 }
]

precios_catalogo_hoteles_data = [
    { 'hotel_id': 24, 'precio_catalogo': 1100 },
    { 'hotel_id': 21, 'precio_catalogo': 1300 }
]

# Simular lógica de UPDATE
habitaciones_actualizadas_por_hotel = set()

# Procesar precios por hotel
print("[PASO 1] Procesando precios_catalogo_hoteles_data:")
for precio_item in precios_catalogo_hoteles_data:
    hotel_id = precio_item.get('hotel_id')
    print(f"  - Hotel {hotel_id}: Se crearian/actualizarian precios para todas sus habitaciones")
    # En el código real, aquí se agregarían los IDs de las habitaciones del hotel
    # Para este ejemplo, asumamos que hotel 24 tiene habitaciones [10, 11, 12]
    # y hotel 21 tiene habitaciones [20, 21, 22]
    if hotel_id == 24:
        habitaciones_actualizadas_por_hotel.update([10, 11, 12])
    elif hotel_id == 21:
        habitaciones_actualizadas_por_hotel.update([20, 21, 22])

print(f"\n  habitaciones_actualizadas_por_hotel: {habitaciones_actualizadas_por_hotel}")

# Procesar precios por habitación
print("\n[PASO 2] Procesando precios_catalogo_data:")
enviados_precios_habitaciones = []
for precio_item in precios_catalogo_data:
    habitacion_id = precio_item.get('habitacion_id')
    print(f"  - Habitacion {habitacion_id}: precio ${precio_item.get('precio_catalogo')}")
    enviados_precios_habitaciones.append(habitacion_id)

print(f"\n  enviados_precios_habitaciones: {enviados_precios_habitaciones}")

# Lógica de eliminación
print("\n[PASO 3] Lógica de eliminación:")
habitaciones_a_mantener = set(enviados_precios_habitaciones) | habitaciones_actualizadas_por_hotel
print(f"  habitaciones_a_mantener: {habitaciones_a_mantener}")
print(f"  Se eliminarian precios de habitaciones que NO esten en este set")

# Simular habitaciones existentes en BD
habitaciones_en_bd = {1, 2, 3, 10, 11, 12, 20, 21, 22, 99}  # 99 es una habitación vieja
print(f"\n[SIMULACION] Habitaciones con precio en BD: {habitaciones_en_bd}")
habitaciones_a_eliminar = habitaciones_en_bd - habitaciones_a_mantener
print(f"[RESULTADO] Se eliminarian precios de: {habitaciones_a_eliminar}")
print(f"[RESULTADO] Se mantendrian precios de: {habitaciones_a_mantener & habitaciones_en_bd}")
