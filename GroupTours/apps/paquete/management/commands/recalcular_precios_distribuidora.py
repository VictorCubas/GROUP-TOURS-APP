# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from apps.paquete.models import Paquete, SalidaPaquete
from decimal import Decimal


class Command(BaseCommand):
    help = 'Recalcula los precios de venta sugeridos para todos los paquetes de distribuidora'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra los cambios sin aplicarlos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN: No se aplicarán cambios'))

        self.stdout.write('=' * 80)
        self.stdout.write('RECALCULAR PRECIOS DE PAQUETES DE DISTRIBUIDORA')
        self.stdout.write('=' * 80)
        self.stdout.write('')

        # Obtener todos los paquetes de distribuidora
        paquetes_distribuidora = Paquete.objects.filter(propio=False)
        total_paquetes = paquetes_distribuidora.count()

        self.stdout.write(f'Total de paquetes de distribuidora: {total_paquetes}')
        self.stdout.write('')

        total_salidas = 0
        total_modificadas = 0
        total_sin_cambios = 0

        for paquete in paquetes_distribuidora:
            self.stdout.write(f'\nPaquete: {paquete.nombre} (ID: {paquete.id})')
            self.stdout.write(f'  Distribuidora: {paquete.distribuidora}')

            salidas = SalidaPaquete.objects.filter(paquete=paquete)
            cant_salidas = salidas.count()
            total_salidas += cant_salidas

            self.stdout.write(f'  Salidas: {cant_salidas}')

            if cant_salidas == 0:
                self.stdout.write(self.style.WARNING('    Sin salidas para procesar'))
                continue

            for salida in salidas:
                # Guardar valores actuales
                precio_min_anterior = salida.precio_venta_sugerido_min
                precio_max_anterior = salida.precio_venta_sugerido_max

                # Calcular nuevos valores (sin guardar aún)
                min_base = Decimal(str(salida.precio_actual))
                max_base = Decimal(str(salida.precio_final)) if salida.precio_final else min_base
                comision = Decimal(str(salida.comision)) if salida.comision else Decimal('0')

                # Para distribuidora NO se suman servicios
                costo_total_min = min_base
                costo_total_max = max_base

                # Aplicar comisión
                if comision > 0:
                    factor = Decimal('1') + (comision / Decimal('100'))
                else:
                    factor = Decimal('1')

                precio_min_nuevo = costo_total_min * factor
                precio_max_nuevo = costo_total_max * factor

                # Verificar si hay cambios
                if precio_min_anterior != precio_min_nuevo or precio_max_anterior != precio_max_nuevo:
                    total_modificadas += 1
                    self.stdout.write(f'    Salida {salida.id} (Fecha: {salida.fecha_salida}):')
                    self.stdout.write(f'      ANTES: min=${precio_min_anterior}, max=${precio_max_anterior}')
                    self.stdout.write(f'      AHORA: min=${precio_min_nuevo}, max=${precio_max_nuevo}')

                    if not dry_run:
                        # Aplicar cambios usando el método del modelo
                        salida.calcular_precio_venta()
                        self.stdout.write(self.style.SUCCESS('      [OK] Actualizado'))
                    else:
                        self.stdout.write(self.style.WARNING('      (No aplicado - dry-run)'))
                else:
                    total_sin_cambios += 1

        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write('RESUMEN')
        self.stdout.write('=' * 80)
        self.stdout.write(f'Total paquetes de distribuidora: {total_paquetes}')
        self.stdout.write(f'Total salidas procesadas: {total_salidas}')
        self.stdout.write(f'Salidas modificadas: {total_modificadas}')
        self.stdout.write(f'Salidas sin cambios: {total_sin_cambios}')
        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING('MODO DRY-RUN ACTIVO'))
            self.stdout.write('Para aplicar los cambios, ejecuta el comando sin --dry-run:')
            self.stdout.write('  python manage.py recalcular_precios_distribuidora')
        else:
            self.stdout.write(self.style.SUCCESS(f'[OK] Se actualizaron {total_modificadas} salidas'))

        self.stdout.write('=' * 80)
