#!/usr/bin/env python
"""Script para diagnosticar el problema de caja con nota de crédito"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica
from apps.arqueo_caja.models import AperturaCaja, Caja

print("="*80)
print("DIAGNÓSTICO DE CAJA Y FACTURA")
print("="*80)

# 1. Verificar factura 49
print("\n1. INFORMACIÓN DE LA FACTURA 49:")
try:
    factura = FacturaElectronica.objects.get(id=49)
    print(f"   - ID: {factura.id}")
    print(f"   - Número: {factura.numero_factura}")
    print(f"   - Punto Expedición: {factura.punto_expedicion}")
    print(f"   - Código PE: {factura.punto_expedicion.codigo if factura.punto_expedicion else 'N/A'}")
    print(f"   - Establecimiento: {factura.punto_expedicion.establecimiento if factura.punto_expedicion else 'N/A'}")
    pe_factura = factura.punto_expedicion
except FacturaElectronica.DoesNotExist:
    print("   ❌ Factura 49 no existe")
    pe_factura = None

# 2. Verificar caja 5
print("\n2. INFORMACIÓN DE LA CAJA 5:")
try:
    caja = Caja.objects.get(id=5)
    print(f"   - ID: {caja.id}")
    print(f"   - Nombre: {caja.nombre}")
    print(f"   - Número: {caja.numero_caja}")
    print(f"   - Punto Expedición: {caja.punto_expedicion}")
    print(f"   - Código PE: {caja.punto_expedicion.codigo if caja.punto_expedicion else 'N/A'}")
    print(f"   - Estado: {caja.estado_actual}")
    print(f"   - Activa: {caja.activo}")
except Caja.DoesNotExist:
    print("   ❌ Caja 5 no existe")
    caja = None

# 3. Verificar aperturas de caja 5
print("\n3. APERTURAS DE CAJA 5:")
if caja:
    aperturas = AperturaCaja.objects.filter(caja=caja, activo=True).order_by('-fecha_hora_apertura')
    for apertura in aperturas:
        print(f"   - Apertura {apertura.codigo_apertura}")
        print(f"     * Abierta: {apertura.esta_abierta}")
        print(f"     * Activa: {apertura.activo}")
        print(f"     * Fecha: {apertura.fecha_hora_apertura}")
        print(f"     * PE de la caja: {apertura.caja.punto_expedicion.codigo if apertura.caja.punto_expedicion else 'N/A'}")

# 4. Buscar aperturas que coincidan con el PE de la factura
print("\n4. BÚSQUEDA DE APERTURA SEGÚN LÓGICA DEL SISTEMA:")
if pe_factura:
    print(f"   Buscando apertura con PE = {pe_factura.codigo}...")
    apertura_encontrada = AperturaCaja.objects.filter(
        caja__punto_expedicion=pe_factura,
        esta_abierta=True,
        activo=True
    ).first()

    if apertura_encontrada:
        print(f"   ✅ APERTURA ENCONTRADA: {apertura_encontrada.codigo_apertura}")
        print(f"      - Caja: {apertura_encontrada.caja.nombre}")
        print(f"      - PE: {apertura_encontrada.caja.punto_expedicion.codigo}")
    else:
        print(f"   ❌ NO SE ENCONTRÓ APERTURA ABIERTA")

        # Verificar todas las aperturas abiertas
        print("\n   Aperturas abiertas en el sistema:")
        todas_abiertas = AperturaCaja.objects.filter(esta_abierta=True, activo=True)
        if todas_abiertas.exists():
            for ap in todas_abiertas:
                print(f"      - {ap.codigo_apertura}: Caja {ap.caja.nombre}, PE: {ap.caja.punto_expedicion.codigo}")
        else:
            print("      No hay ninguna apertura abierta en el sistema")

# 5. Comparación
print("\n5. COMPARACIÓN:")
if pe_factura and caja:
    if caja.punto_expedicion == pe_factura:
        print("   ✅ El PE de la factura COINCIDE con el PE de la caja 5")
    else:
        print("   ❌ PROBLEMA: El PE de la factura NO COINCIDE con el PE de la caja 5")
        print(f"      - PE Factura: {pe_factura.codigo}")
        print(f"      - PE Caja 5: {caja.punto_expedicion.codigo if caja.punto_expedicion else 'N/A'}")

print("\n" + "="*80)
