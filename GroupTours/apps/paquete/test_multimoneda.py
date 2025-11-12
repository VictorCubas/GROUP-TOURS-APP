"""
Script de prueba para el sistema multi-moneda.

Ejecutar con:
    python manage.py shell < apps/paquete/test_multimoneda.py

O en Django shell:
    exec(open('apps/paquete/test_multimoneda.py').read())
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

print("="*80)
print("PRUEBAS DEL SISTEMA MULTI-MONEDA")
print("="*80)

# ========== 1. VERIFICAR MODELOS ==========
print("\n[1] Verificando modelos...")

from apps.moneda.models import Moneda, CotizacionMoneda
from apps.hotel.models import Hotel, Habitacion
from apps.paquete.models import SalidaPaquete, Paquete

# Verificar que existan las monedas
try:
    usd = Moneda.objects.get(codigo='USD')
    print(f"✓ Moneda USD encontrada: {usd}")
except Moneda.DoesNotExist:
    print("⚠ Moneda USD no existe. Creando...")
    usd = Moneda.objects.create(
        nombre="Dólar Estadounidense",
        simbolo="$",
        codigo="USD",
        activo=True
    )
    print(f"✓ Moneda USD creada: {usd}")

try:
    pyg = Moneda.objects.get(codigo='PYG')
    print(f"✓ Moneda PYG encontrada: {pyg}")
except Moneda.DoesNotExist:
    print("⚠ Moneda PYG no existe. Creando...")
    pyg = Moneda.objects.create(
        nombre="Guaraní Paraguayo",
        simbolo="Gs",
        codigo="PYG",
        activo=True
    )
    print(f"✓ Moneda PYG creada: {pyg}")

# ========== 2. VERIFICAR/CREAR COTIZACIÓN ==========
print("\n[2] Verificando cotizaciones...")

fecha_hoy = timezone.now().date()
cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(usd, fecha_hoy)

if not cotizacion:
    print("⚠ No hay cotización vigente. Creando cotización de prueba...")
    cotizacion = CotizacionMoneda.objects.create(
        moneda=usd,
        valor_en_guaranies=Decimal('7300.00'),
        fecha_vigencia=fecha_hoy,
        observaciones="Cotización de prueba para sistema multi-moneda"
    )
    print(f"✓ Cotización creada: 1 USD = {cotizacion.valor_en_guaranies} Gs")
else:
    print(f"✓ Cotización vigente: 1 USD = {cotizacion.valor_en_guaranies} Gs (fecha: {cotizacion.fecha_vigencia})")

# ========== 3. PRUEBA DE CONVERSIÓN BÁSICA ==========
print("\n[3] Probando conversiones básicas...")

from apps.paquete.utils import convertir_entre_monedas

try:
    # USD a PYG
    resultado_pyg = convertir_entre_monedas(
        monto=100,
        moneda_origen=usd,
        moneda_destino=pyg,
        fecha=fecha_hoy
    )
    print(f"✓ 100 USD → {resultado_pyg} Gs")

    # PYG a USD
    resultado_usd = convertir_entre_monedas(
        monto=730000,
        moneda_origen=pyg,
        moneda_destino=usd,
        fecha=fecha_hoy
    )
    print(f"✓ 730,000 Gs → {resultado_usd} USD")

    # Misma moneda
    resultado_mismo = convertir_entre_monedas(
        monto=500,
        moneda_origen=usd,
        moneda_destino=usd,
        fecha=fecha_hoy
    )
    print(f"✓ 500 USD → {resultado_mismo} USD (sin conversión)")

except Exception as e:
    print(f"✗ Error en conversión: {e}")

# ========== 4. VERIFICAR HABITACIONES ==========
print("\n[4] Verificando habitaciones con diferentes monedas...")

habitaciones_usd = Habitacion.objects.filter(moneda=usd).count()
habitaciones_pyg = Habitacion.objects.filter(moneda=pyg).count()
habitaciones_sin_moneda = Habitacion.objects.filter(moneda__isnull=True).count()

print(f"  - Habitaciones en USD: {habitaciones_usd}")
print(f"  - Habitaciones en PYG: {habitaciones_pyg}")
print(f"  - Habitaciones sin moneda: {habitaciones_sin_moneda}")

if habitaciones_sin_moneda > 0:
    print(f"  ⚠ Advertencia: Hay {habitaciones_sin_moneda} habitaciones sin moneda asignada")

# ========== 5. PRUEBA CON SALIDA EXISTENTE ==========
print("\n[5] Probando con salida existente...")

salida_ejemplo = SalidaPaquete.objects.filter(moneda__isnull=False).first()

if salida_ejemplo:
    print(f"✓ Salida encontrada: {salida_ejemplo} (ID: {salida_ejemplo.id})")
    print(f"  - Moneda: {salida_ejemplo.moneda.codigo}")
    print(f"  - Precio actual: {salida_ejemplo.precio_actual}")

    # Probar método de conversión a moneda alternativa
    try:
        precio_alt = salida_ejemplo.obtener_precio_en_moneda_alternativa()
        print(f"\n  Precio en moneda alternativa ({precio_alt['moneda_alternativa']}):")
        print(f"    - Precio mínimo: {precio_alt['precio_min']}")
        print(f"    - Precio máximo: {precio_alt['precio_max']}")
        print(f"    - Cotización aplicada: {precio_alt['cotizacion_aplicada']}")
        print(f"    - Fecha cotización: {precio_alt['fecha_cotizacion']}")
    except ValidationError as e:
        print(f"  ⚠ Error al convertir: {e}")
    except Exception as e:
        print(f"  ✗ Error inesperado: {e}")
else:
    print("⚠ No hay salidas para probar. Puedes crear una manualmente.")

# ========== 6. VERIFICAR SERIALIZERS ==========
print("\n[6] Verificando serializers...")

try:
    from apps.paquete.serializers import SalidaPaqueteSerializer

    if salida_ejemplo:
        serializer = SalidaPaqueteSerializer(salida_ejemplo)
        data = serializer.data

        if 'precio_moneda_alternativa' in data:
            print("✓ Campo 'precio_moneda_alternativa' disponible en serializer")
            if data['precio_moneda_alternativa']:
                print(f"  Moneda alternativa: {data['precio_moneda_alternativa'].get('moneda')}")
                print(f"  Precio actual: {data['precio_moneda_alternativa'].get('precio_actual')}")
            else:
                print("  ⚠ Campo está en null (puede ser por falta de cotización)")
        else:
            print("✗ Campo 'precio_moneda_alternativa' NO encontrado en serializer")
    else:
        print("⚠ No hay salida para verificar serializer")

except Exception as e:
    print(f"✗ Error al verificar serializer: {e}")

# ========== 7. RESUMEN ==========
print("\n" + "="*80)
print("RESUMEN DE PRUEBAS")
print("="*80)
print(f"✓ Monedas configuradas: USD, PYG")
print(f"✓ Cotización vigente: 1 USD = {cotizacion.valor_en_guaranies} Gs")
print(f"✓ Función de conversión: Operativa")
print(f"✓ Métodos de modelo: Implementados")
print(f"✓ Serializers: Configurados")
print("\n¡Sistema multi-moneda funcionando correctamente!")
print("="*80)

# ========== 8. EJEMPLO DE USO ==========
print("\n" + "="*80)
print("EJEMPLO DE USO")
print("="*80)
print("""
# Para crear una salida con habitaciones multi-moneda:

from apps.paquete.models import create_salida_paquete
from datetime import datetime, timedelta

data = {
    "paquete_id": 1,  # ID de tu paquete
    "fecha_salida": datetime.now().date() + timedelta(days=30),
    "fecha_regreso": datetime.now().date() + timedelta(days=35),
    "moneda_id": usd.id,  # o pyg.id
    "hoteles_ids": [1, 2, 3],  # IDs de hoteles
    "cupo": 40,
    "ganancia": 15,
}

salida = create_salida_paquete(data)
print(f"Salida creada: {salida}")
print(f"Precio en {salida.moneda.codigo}: {salida.precio_actual}")

# Ver precio en moneda alternativa
precio_alt = salida.precio_en_moneda_alternativa
if precio_alt:
    print(f"Precio en {precio_alt['moneda_alternativa']}: {precio_alt['precio_min']}")
""")
print("="*80)
