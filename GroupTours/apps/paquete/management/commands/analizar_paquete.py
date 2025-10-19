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
        for ps in paquete.paquete_servicios.all():
            precio = ps.precio if ps.precio and ps.precio > 0 else (ps.servicio.precio if hasattr(ps.servicio, 'precio') else Decimal('0'))
            total_servicios += precio
            self.stdout.write(f'  - {ps.servicio.nombre}: ${precio}')
        self.stdout.write(f'\nTotal servicios: ${total_servicios}')
        self.stdout.write('')

        # Obtener habitaciones con cupo en esta salida
        self.stdout.write('=' * 80)
        self.stdout.write('HABITACIONES DISPONIBLES EN ESTA SALIDA')
        self.stdout.write('=' * 80)
        cupos = CupoHabitacionSalida.objects.filter(salida=salida).select_related('habitacion', 'habitacion__hotel')

        habitaciones_precios = []

        for cupo in cupos:
            hab = cupo.habitacion

            # Calcular precio por noche de esta habitacion
            precio_noche = hab.precio_noche or Decimal('0')

            # Precio total de habitacion (noches)
            precio_hab_total = precio_noche * noches

            # Costo base (habitacion + servicios)
            costo_base = precio_hab_total + total_servicios

            # Aplicar ganancia/comision
            ganancia = salida.ganancia or Decimal('0')
            comision = salida.comision or Decimal('0')

            if paquete.propio and ganancia > 0:
                factor = Decimal('1') + (ganancia / Decimal('100'))
            elif not paquete.propio and comision > 0:
                factor = Decimal('1') + (comision / Decimal('100'))
            else:
                factor = Decimal('1')

            # Precio de venta final
            precio_venta = costo_base * factor

            habitaciones_precios.append({
                'hotel': hab.hotel.nombre,
                'habitacion_id': hab.id,
                'tipo': hab.tipo,
                'precio_noche': precio_noche,
                'precio_hab_total': precio_hab_total,
                'costo_base': costo_base,
                'precio_venta': precio_venta,
                'cupo': cupo.cupo
            })

            self.stdout.write(f'\nHotel: {hab.hotel.nombre}')
            self.stdout.write(f'  Habitacion ID: {hab.id} - Tipo: {hab.tipo}')
            self.stdout.write(f'  Precio por noche: ${precio_noche}')
            self.stdout.write(f'  Precio habitacion ({noches} noches): ${precio_hab_total}')
            self.stdout.write(f'  + Servicios: ${total_servicios}')
            self.stdout.write(f'  = Costo base: ${costo_base}')
            self.stdout.write(f'  Factor aplicado: {factor} (ganancia {ganancia}% / comision {comision}%)')
            self.stdout.write(f'  PRECIO DE VENTA FINAL: ${precio_venta}')
            self.stdout.write(f'  Cupo disponible: {cupo.cupo}')

        self.stdout.write('')
        self.stdout.write('=' * 80)

        # Encontrar la mas barata y la mas cara
        if habitaciones_precios:
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

            self.stdout.write('')
            self.stdout.write('=' * 80)
            self.stdout.write('RESUMEN DE TODAS LAS HABITACIONES (ordenadas por precio)')
            self.stdout.write('=' * 80)
            habitaciones_ordenadas = sorted(habitaciones_precios, key=lambda x: x['precio_venta'])
            for idx, hab in enumerate(habitaciones_ordenadas, 1):
                self.stdout.write(
                    f"{idx}. {hab['hotel']} - Habitacion {hab['habitacion_id']} ({hab['tipo']}): ${hab['precio_venta']}"
                )
        else:
            self.stdout.write(self.style.WARNING('No hay habitaciones con cupo en esta salida'))

        self.stdout.write('')
        self.stdout.write('=' * 80)
