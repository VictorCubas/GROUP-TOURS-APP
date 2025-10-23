# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from apps.paquete.models import Paquete, SalidaPaquete, CupoHabitacionSalida
from decimal import Decimal


class Command(BaseCommand):
    help = 'Analiza precios de paquetes turisticos mostrando cual habitacion da el precio minimo y maximo'

    def add_arguments(self, parser):
        parser.add_argument('paquete_id', type=int, help='ID del paquete a analizar')
        parser.add_argument('salida_id', type=int, help='ID de la salida a analizar')

    def handle(self, *args, **options):
        paquete_id = options['paquete_id']
        salida_id = options['salida_id']

        try:
            paquete = Paquete.objects.get(id=paquete_id)
            salida = SalidaPaquete.objects.get(id=salida_id)
        except Paquete.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Paquete con ID {paquete_id} no encontrado'))
            return
        except SalidaPaquete.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Salida con ID {salida_id} no encontrada'))
            return

        self.stdout.write('=' * 80)
        self.stdout.write('ANALISIS DE PAQUETE Y SALIDA')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Paquete: {paquete.nombre}')
        self.stdout.write(f'Paquete propio: {paquete.propio}')
        self.stdout.write(f'Salida ID: {salida.id}')
        self.stdout.write(f'Fecha salida: {salida.fecha_salida}')
        self.stdout.write(f'Fecha regreso: {salida.fecha_regreso}')
        self.stdout.write(f'Ganancia: {salida.ganancia}%')
        self.stdout.write(f'Comision: {salida.comision}%')
        self.stdout.write(f'Precio actual (min): {salida.precio_actual}')
        self.stdout.write(f'Precio final (max): {salida.precio_final}')
        self.stdout.write(f'Precio venta sugerido min: {salida.precio_venta_sugerido_min}')
        self.stdout.write(f'Precio venta sugerido max: {salida.precio_venta_sugerido_max}')
        self.stdout.write('')

        # Calcular noches
        if salida.fecha_regreso and salida.fecha_salida:
            noches = (salida.fecha_regreso - salida.fecha_salida).days
        else:
            noches = 1
        self.stdout.write(f'Cantidad de noches: {noches}')
        self.stdout.write('')

        # Obtener servicios del paquete
        self.stdout.write('=' * 80)
        self.stdout.write('SERVICIOS DEL PAQUETE')
        self.stdout.write('=' * 80)
        total_servicios = Decimal('0')

        if paquete.propio:
            # Solo para paquetes propios se calculan los servicios
            for ps in paquete.paquete_servicios.all():
                precio = ps.precio if ps.precio and ps.precio > 0 else (ps.servicio.precio if hasattr(ps.servicio, 'precio') else Decimal('0'))
                total_servicios += precio
                self.stdout.write(f'  - {ps.servicio.nombre}: ${precio}')
            self.stdout.write(f'\nTotal servicios: ${total_servicios}')
        else:
            self.stdout.write('  (Paquete de distribuidora - servicios incluidos en precio base)')

        self.stdout.write('')

        # Obtener habitaciones con cupo en esta salida
        self.stdout.write('=' * 80)
        self.stdout.write('HABITACIONES DISPONIBLES EN ESTA SALIDA')
        self.stdout.write('=' * 80)
        cupos = CupoHabitacionSalida.objects.filter(salida=salida).select_related('habitacion', 'habitacion__hotel')

        habitaciones_precios = []

        # Obtener ganancia/comision
        ganancia = salida.ganancia or Decimal('0')
        comision = salida.comision or Decimal('0')

        for cupo in cupos:
            hab = cupo.habitacion

            if paquete.propio:
                # PAQUETE PROPIO: Calcular desde precio de habitacion + servicios
                precio_noche = hab.precio_noche or Decimal('0')
                precio_hab_total = precio_noche * noches
                costo_base = precio_hab_total + total_servicios

                # Aplicar ganancia
                if ganancia > 0:
                    factor = Decimal('1') + (ganancia / Decimal('100'))
                else:
                    factor = Decimal('1')

                precio_venta = costo_base * factor

                habitaciones_precios.append({
                    'hotel': hab.hotel.nombre,
                    'habitacion_id': hab.id,
                    'tipo': hab.tipo,
                    'precio_noche': precio_noche,
                    'precio_hab_total': precio_hab_total,
                    'costo_base': costo_base,
                    'precio_venta': precio_venta,
                    'cupo': cupo.cupo,
                    'es_propio': True
                })

                self.stdout.write(f'\nHotel: {hab.hotel.nombre}')
                self.stdout.write(f'  Habitacion ID: {hab.id} - Tipo: {hab.tipo}')
                self.stdout.write(f'  Precio por noche: ${precio_noche}')
                self.stdout.write(f'  Precio habitacion ({noches} noches): ${precio_hab_total}')
                self.stdout.write(f'  + Servicios: ${total_servicios}')
                self.stdout.write(f'  = Costo base: ${costo_base}')
                self.stdout.write(f'  Factor aplicado: {factor} (ganancia {ganancia}%)')
                self.stdout.write(f'  PRECIO DE VENTA FINAL: ${precio_venta}')
                self.stdout.write(f'  Cupo disponible: {cupo.cupo}')

            else:
                # PAQUETE DE DISTRIBUIDORA: Usar precio_actual/precio_final de la salida
                # Cada habitacion toma el precio base de la salida (sin desglose)
                # El precio_noche no se usa porque viene de distribuidora

                # Determinar si esta habitacion corresponde al min o max
                # Esto es una simplificacion: asumimos que el tipo de habitacion determina el precio
                # En realidad, deberiamos tener un campo que indique cual habitacion es min/max

                # Por ahora, usaremos precio_actual como base para todas
                costo_base_distribuidora = salida.precio_actual

                # Aplicar comision
                if comision > 0:
                    factor = Decimal('1') + (comision / Decimal('100'))
                else:
                    factor = Decimal('1')

                precio_venta = costo_base_distribuidora * factor

                habitaciones_precios.append({
                    'hotel': hab.hotel.nombre,
                    'habitacion_id': hab.id,
                    'tipo': hab.tipo,
                    'precio_noche': None,
                    'precio_hab_total': None,
                    'costo_base': costo_base_distribuidora,
                    'precio_venta': precio_venta,
                    'cupo': cupo.cupo,
                    'es_propio': False
                })

                self.stdout.write(f'\nHotel: {hab.hotel.nombre}')
                self.stdout.write(f'  Habitacion ID: {hab.id} - Tipo: {hab.tipo}')
                self.stdout.write(f'  Precio por noche: (No aplica - paquete de distribuidora)')
                self.stdout.write(f'  Costo base (desde distribuidora): ${costo_base_distribuidora}')
                self.stdout.write(f'  Factor aplicado: {factor} (comision {comision}%)')
                self.stdout.write(f'  PRECIO DE VENTA FINAL: ${precio_venta}')
                self.stdout.write(f'  Cupo disponible: {cupo.cupo}')

        self.stdout.write('')
        self.stdout.write('=' * 80)

        # Encontrar la mas barata y la mas cara
        if habitaciones_precios:
            if paquete.propio:
                # Para paquetes propios, buscar min y max
                mas_barata = min(habitaciones_precios, key=lambda x: x['precio_venta'])
                mas_cara = max(habitaciones_precios, key=lambda x: x['precio_venta'])

                self.stdout.write(self.style.SUCCESS('HABITACION MAS BARATA (precio_venta_total_min)'))
                self.stdout.write('=' * 80)
                self.stdout.write(f'Hotel: {mas_barata["hotel"]}')
                self.stdout.write(f'Habitacion ID: {mas_barata["habitacion_id"]}')
                self.stdout.write(f'Tipo: {mas_barata["tipo"]}')
                self.stdout.write(f'Precio de venta: ${mas_barata["precio_venta"]}')
                self.stdout.write(f'Cupo disponible: {mas_barata["cupo"]}')
                self.stdout.write('')
                coincide_min = mas_barata["precio_venta"] == salida.precio_venta_sugerido_min
                if coincide_min:
                    self.stdout.write(self.style.SUCCESS(
                        f'[OK] Coincide con precio_venta_sugerido_min ({salida.precio_venta_sugerido_min})'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'[ERROR] NO coincide con precio_venta_sugerido_min ({salida.precio_venta_sugerido_min})'
                    ))

                self.stdout.write('')
                self.stdout.write('=' * 80)
                self.stdout.write(self.style.SUCCESS('HABITACION MAS CARA (precio_venta_total_max)'))
                self.stdout.write('=' * 80)
                self.stdout.write(f'Hotel: {mas_cara["hotel"]}')
                self.stdout.write(f'Habitacion ID: {mas_cara["habitacion_id"]}')
                self.stdout.write(f'Tipo: {mas_cara["tipo"]}')
                self.stdout.write(f'Precio de venta: ${mas_cara["precio_venta"]}')
                self.stdout.write(f'Cupo disponible: {mas_cara["cupo"]}')
                self.stdout.write('')
                coincide_max = mas_cara["precio_venta"] == salida.precio_venta_sugerido_max
                if coincide_max:
                    self.stdout.write(self.style.SUCCESS(
                        f'[OK] Coincide con precio_venta_sugerido_max ({salida.precio_venta_sugerido_max})'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'[ERROR] NO coincide con precio_venta_sugerido_max ({salida.precio_venta_sugerido_max})'
                    ))

            else:
                # Para paquetes de distribuidora, todas las habitaciones tienen el mismo precio base
                # Pero mostramos la informacion de todas las habitaciones disponibles
                self.stdout.write(self.style.SUCCESS('PRECIO DE VENTA (PAQUETE DE DISTRIBUIDORA)'))
                self.stdout.write('=' * 80)
                self.stdout.write('NOTA: En paquetes de distribuidora, todas las habitaciones')
                self.stdout.write('      tienen el mismo costo base desde la distribuidora.')
                self.stdout.write(f'      Costo base: ${salida.precio_actual}')
                self.stdout.write(f'      Comision aplicada: {comision}%')
                if habitaciones_precios:
                    self.stdout.write(f'      Precio de venta final: ${habitaciones_precios[0]["precio_venta"]}')
                self.stdout.write('')
                coincide = habitaciones_precios[0]["precio_venta"] == salida.precio_venta_sugerido_min
                if coincide:
                    self.stdout.write(self.style.SUCCESS(
                        f'[OK] Coincide con precio_venta_sugerido_min/max ({salida.precio_venta_sugerido_min})'
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        f'[ERROR] NO coincide con precio_venta_sugerido ({salida.precio_venta_sugerido_min})'
                    ))

            self.stdout.write('')
            self.stdout.write('=' * 80)
            self.stdout.write('RESUMEN DE TODAS LAS HABITACIONES')
            self.stdout.write('=' * 80)
            if paquete.propio:
                habitaciones_ordenadas = sorted(habitaciones_precios, key=lambda x: x['precio_venta'])
                for idx, hab in enumerate(habitaciones_ordenadas, 1):
                    self.stdout.write(
                        f"{idx}. {hab['hotel']} - Habitacion {hab['habitacion_id']} ({hab['tipo']}): ${hab['precio_venta']}"
                    )
            else:
                for idx, hab in enumerate(habitaciones_precios, 1):
                    self.stdout.write(
                        f"{idx}. {hab['hotel']} - Habitacion {hab['habitacion_id']} ({hab['tipo']}): ${hab['precio_venta']} (cupo: {hab['cupo']})"
                    )
        else:
            self.stdout.write(self.style.WARNING('No hay habitaciones con cupo en esta salida'))

        self.stdout.write('')
        self.stdout.write('=' * 80)
