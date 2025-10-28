"""
Comando de Django para recalcular los estados de todas las reservas existentes.

Uso:
    python manage.py recalcular_estados_reservas

Opciones:
    --dry-run : Muestra los cambios sin aplicarlos
    --estado ESTADO : Solo procesar reservas con estado específico
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from apps.reserva.models import Reserva


class Command(BaseCommand):
    help = 'Recalcula los estados de todas las reservas según la lógica actualizada'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra los cambios sin aplicarlos a la base de datos',
        )
        parser.add_argument(
            '--estado',
            type=str,
            help='Filtrar por estado específico (pendiente, confirmada, finalizada, cancelada)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        estado_filtro = options.get('estado')

        # Banner
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '='*70))
        self.stdout.write(self.style.MIGRATE_HEADING('  RECALCULO DE ESTADOS DE RESERVAS'))
        self.stdout.write(self.style.MIGRATE_HEADING('='*70 + '\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('[!] MODO DRY-RUN: No se aplicaran cambios\n'))

        # Construir queryset
        queryset = Reserva.objects.select_related('salida', 'habitacion', 'paquete').prefetch_related('pasajeros')

        if estado_filtro:
            queryset = queryset.filter(estado=estado_filtro)
            self.stdout.write(f'Filtrando por estado: {estado_filtro}\n')

        # Excluir canceladas (no se recalculan)
        queryset = queryset.exclude(estado='cancelada')

        total = queryset.count()
        self.stdout.write(f'Total de reservas a procesar: {total}\n')

        if total == 0:
            self.stdout.write(self.style.WARNING('No hay reservas para procesar.'))
            return

        # Contadores
        cambios = 0
        sin_cambios = 0
        errores = 0
        estadisticas = {
            'pendiente': 0,
            'confirmada': 0,
            'finalizada': 0,
        }

        self.stdout.write('\n' + '-'*70)
        self.stdout.write('Procesando reservas...\n')
        self.stdout.write('-'*70 + '\n')

        for i, reserva in enumerate(queryset, 1):
            try:
                estado_anterior = reserva.estado

                # Calcular el nuevo estado SIN guardar
                # Simulamos la lógica de actualizar_estado() manualmente
                nuevo_estado = self._calcular_nuevo_estado(reserva)

                # Comparar
                if estado_anterior != nuevo_estado:
                    cambios += 1

                    # Mostrar información del cambio
                    info = (
                        f'[{i}/{total}] Reserva {reserva.codigo} '
                        f'({estado_anterior} -> {nuevo_estado})'
                    )

                    # Detalles adicionales
                    detalles = []
                    detalles.append(f'Monto pagado: ${reserva.monto_pagado}')
                    detalles.append(f'Seña total: ${reserva.seña_total}')
                    detalles.append(f'Costo total: ${reserva.costo_total_estimado}')
                    detalles.append(f'Pasajeros: {reserva.pasajeros_cargados}/{reserva.cantidad_pasajeros}')

                    self.stdout.write(self.style.WARNING(info))
                    for detalle in detalles:
                        self.stdout.write(f'    {detalle}')
                    self.stdout.write('')

                    # Aplicar cambio si no es dry-run
                    if not dry_run:
                        reserva.estado = nuevo_estado
                        reserva.datos_completos = not reserva.faltan_datos_pasajeros
                        reserva.save(update_fields=['estado', 'datos_completos'])

                    estadisticas[nuevo_estado] += 1
                else:
                    sin_cambios += 1

            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(f'[{i}/{total}] Error en reserva {reserva.codigo}: {str(e)}')
                )

        # Resumen final
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.MIGRATE_HEADING('  RESUMEN'))
        self.stdout.write('='*70 + '\n')

        self.stdout.write(f'Total procesadas: {total}')
        self.stdout.write(self.style.SUCCESS(f'[OK] Con cambios: {cambios}'))
        self.stdout.write(f'  Sin cambios: {sin_cambios}')

        if errores > 0:
            self.stdout.write(self.style.ERROR(f'[ERROR] Errores: {errores}'))

        if cambios > 0:
            self.stdout.write('\nNuevos estados:')
            for estado, cantidad in estadisticas.items():
                if cantidad > 0:
                    self.stdout.write(f'  - {estado.capitalize()}: {cantidad}')

        if dry_run and cambios > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[!] {cambios} reserva(s) necesitan actualizacion. '
                    'Ejecuta sin --dry-run para aplicar los cambios.'
                )
            )
        elif cambios > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] {cambios} reserva(s) actualizadas correctamente.'
                )
            )

        self.stdout.write('')

    def _calcular_nuevo_estado(self, reserva):
        """
        Replica la lógica de actualizar_estado() sin modificar la base de datos.
        """
        if reserva.estado == "cancelada":
            return "cancelada"

        # Si pago total (100%) + datos completos → Finalizada
        if reserva.esta_totalmente_pagada() and not reserva.faltan_datos_pasajeros:
            return "finalizada"

        # Si se pagó la seña mínima (o más, pero no el 100%) → Confirmada
        elif reserva.puede_confirmarse():
            return "confirmada"

        # Sin pago suficiente para la seña → Pendiente
        else:
            return "pendiente"
