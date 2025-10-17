"""
Comando para migrar reservas con estado 'incompleta' (legacy) a 'confirmada'.

Uso:
    python manage.py migrar_estados_incompleta
    python manage.py migrar_estados_incompleta --dry-run
"""

from django.core.management.base import BaseCommand
from apps.reserva.models import Reserva


class Command(BaseCommand):
    help = 'Migra reservas con estado "incompleta" (legacy) a "confirmada"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra los cambios sin aplicarlos a la base de datos',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Banner
        self.stdout.write(self.style.MIGRATE_HEADING('\n' + '='*70))
        self.stdout.write(self.style.MIGRATE_HEADING('  MIGRACION DE ESTADOS: incompleta -> confirmada'))
        self.stdout.write(self.style.MIGRATE_HEADING('='*70 + '\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('[!] MODO DRY-RUN: No se aplicaran cambios\n'))

        # Buscar reservas con estado incompleta
        reservas_incompletas = Reserva.objects.filter(estado='incompleta')
        total = reservas_incompletas.count()

        self.stdout.write(f'Total de reservas con estado "incompleta": {total}\n')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay reservas con estado "incompleta" para migrar.'))
            return

        self.stdout.write('-'*70)
        self.stdout.write('Procesando...\n')
        self.stdout.write('-'*70 + '\n')

        # Procesar cada reserva
        for i, reserva in enumerate(reservas_incompletas, 1):
            info = f'[{i}/{total}] Reserva {reserva.codigo}'

            # Mostrar información
            detalles = []
            detalles.append(f'Estado: incompleta -> confirmada')
            detalles.append(f'Pasajeros: {reserva.pasajeros_cargados}/{reserva.cantidad_pasajeros}')
            detalles.append(f'Datos completos: {not reserva.faltan_datos_pasajeros}')

            self.stdout.write(self.style.WARNING(info))
            for detalle in detalles:
                self.stdout.write(f'    {detalle}')
            self.stdout.write('')

            # Aplicar cambio si no es dry-run
            if not dry_run:
                reserva.estado = 'confirmada'
                reserva.datos_completos = not reserva.faltan_datos_pasajeros
                reserva.save(update_fields=['estado', 'datos_completos'])

        # Resumen
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.MIGRATE_HEADING('  RESUMEN'))
        self.stdout.write('='*70 + '\n')

        self.stdout.write(f'Total procesadas: {total}')

        if dry_run and total > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[!] {total} reserva(s) necesitan migracion. '
                    'Ejecuta sin --dry-run para aplicar los cambios.'
                )
            )
        elif total > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n[OK] {total} reserva(s) migradas correctamente de "incompleta" a "confirmada".'
                )
            )

        self.stdout.write('')
