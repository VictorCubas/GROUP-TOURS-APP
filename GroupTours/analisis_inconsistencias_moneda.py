import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva, Pasajero
from decimal import Decimal

print('=' * 80)
print('ANALISIS DE INCONSISTENCIAS DE MONEDA EN RESERVAS')
print('=' * 80)

# 1. Buscar reservas con problemas similares a la 272
print('\n1. BUSCANDO RESERVAS CON PORCENTAJES ANORMALES (>1000%)...\n')

reservas_problematicas = []
total_reservas = Reserva.objects.filter(activo=True).count()

for reserva in Reserva.objects.filter(activo=True).select_related('paquete', 'paquete__moneda', 'salida'):
    for pasajero in reserva.pasajeros.all():
        try:
            porcentaje = pasajero.porcentaje_pagado
            if porcentaje > 1000:  # Porcentaje anormal
                reservas_problematicas.append({
                    'reserva_id': reserva.id,
                    'reserva_codigo': reserva.codigo,
                    'pasajero_id': pasajero.id,
                    'paquete_moneda': reserva.paquete.moneda.codigo if reserva.paquete and reserva.paquete.moneda else 'N/A',
                    'precio_asignado': pasajero.precio_asignado,
                    'monto_pagado': pasajero.monto_pagado,
                    'porcentaje_pagado': porcentaje,
                    'sena_salida': reserva.salida.senia if reserva.salida else None,
                })
        except Exception as e:
            print(f'Error en reserva {reserva.id}, pasajero {pasajero.id}: {e}')

print(f'Total de reservas analizadas: {total_reservas}')
print(f'Reservas con problemas encontradas: {len(reservas_problematicas)}')

if reservas_problematicas:
    print('\nDETALLE DE RESERVAS PROBLEMATICAS:')
    print('-' * 80)
    for item in reservas_problematicas:
        print(f"\nReserva: {item['reserva_codigo']} (ID: {item['reserva_id']})")
        print(f"  Pasajero ID: {item['pasajero_id']}")
        print(f"  Moneda paquete: {item['paquete_moneda']}")
        print(f"  Precio asignado: {item['precio_asignado']}")
        print(f"  Monto pagado: {item['monto_pagado']}")
        print(f"  Porcentaje pagado: {item['porcentaje_pagado']:.2f}%")
        print(f"  Sena esperada: {item['sena_salida']}")
        
        # Diagnostico
        if item['paquete_moneda'] == 'PYG':
            if item['precio_asignado'] and item['precio_asignado'] < 10000:
                print(f"  [PROBLEMA] Precio asignado muy bajo para PYG (deberia ser > 10,000)")
            if item['sena_salida'] and item['sena_salida'] > 100000:
                print(f"  [OK] Sena en rango de guaranies")
        elif item['paquete_moneda'] == 'USD':
            if item['precio_asignado'] and item['precio_asignado'] > 10000:
                print(f"  [PROBLEMA] Precio asignado muy alto para USD (deberia ser < 10,000)")

# 2. Analisis especifico de la reserva 272
print('\n' + '=' * 80)
print('2. ANALISIS DETALLADO DE RESERVA 272')
print('=' * 80)

try:
    r272 = Reserva.objects.get(id=272)
    print(f'\nReserva ID: {r272.id}')
    print(f'Codigo: {r272.codigo}')
    print(f'Fecha creacion: {r272.fecha_reserva}')
    print(f'Estado: {r272.estado}')
    print(f'Paquete: {r272.paquete.nombre if r272.paquete else "N/A"}')
    print(f'Moneda paquete: {r272.paquete.moneda.codigo if r272.paquete and r272.paquete.moneda else "N/A"}')
    print(f'Precio unitario (reserva): {r272.precio_unitario}')
    print(f'Precio base paquete (calculado): {r272.precio_base_paquete}')
    print(f'Sena por pasajero: {r272.salida.senia if r272.salida else "N/A"}')
    print(f'Sena total: {r272.seña_total}')
    print(f'Monto pagado total: {r272.monto_pagado}')
    
    print('\nPASAJEROS:')
    for p in r272.pasajeros.all():
        print(f'\n  Pasajero ID {p.id}: {p.persona.nombre} {p.persona.apellido}')
        print(f'    Precio asignado: {p.precio_asignado}')
        print(f'    Monto pagado: {p.monto_pagado}')
        print(f'    Porcentaje pagado: {p.porcentaje_pagado}%')
        print(f'    Saldo pendiente: {p.saldo_pendiente}')
        
        # Ver como se calcula precio_base_paquete
        precio_calculado = r272.calcular_precio_unitario()
        print(f'\n    DIAGNOSTICO:')
        print(f'    - Precio calculado dinamicamente: {precio_calculado}')
        print(f'    - Diferencia vs precio_asignado: {precio_calculado - (p.precio_asignado or Decimal("0"))}')
        
        if r272.paquete and r272.paquete.moneda:
            if r272.paquete.moneda.codigo == 'PYG' and p.precio_asignado and p.precio_asignado < 10000:
                print(f'    [PROBLEMA CONFIRMADO] Precio en USD pero deberia estar en PYG')
                print(f'    [SUGERENCIA] Deberia ser aprox: {p.precio_asignado * Decimal("7300")} Gs')
        
        # Ver distribuciones
        print(f'\n    Distribuciones de pago:')
        for dist in p.distribuciones_pago.all():
            comp = dist.comprobante
            print(f'      - {comp.numero_comprobante}: {dist.monto} Gs ({comp.tipo}) - {comp.fecha_pago}')

except Reserva.DoesNotExist:
    print('La reserva 272 no existe')
except Exception as e:
    print(f'Error al analizar reserva 272: {e}')
    import traceback
    traceback.print_exc()

# 3. Recomendaciones
print('\n' + '=' * 80)
print('3. RECOMENDACIONES')
print('=' * 80)

if reservas_problematicas:
    print(f'\n[CRITICO] Se encontraron {len(reservas_problematicas)} reservas con problemas de moneda.')
    print('\nACCIONES RECOMENDADAS:')
    print('1. Corregir el precio_asignado de cada pasajero problematico')
    print('2. Script sugerido para correccion:')
    print('\n# Ejemplo de correccion (NO ejecutar automaticamente):')
    print('# pasajero = Pasajero.objects.get(id=529)')
    print('# pasajero.precio_asignado = [VALOR_CORRECTO_EN_PYG]')
    print('# pasajero.save()')
    print('\n3. Validar que el precio_unitario de la reserva este correcto')
    print('4. Revisar el metodo calcular_precio_unitario() para prevenir el problema')
else:
    print('\n[OK] No se encontraron mas reservas con problemas similares a la 272.')

print('\n' + '=' * 80)
print('ANALISIS COMPLETADO')
print('=' * 80)

