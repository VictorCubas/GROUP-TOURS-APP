"""
Comando para eliminar paquetes de forma segura.

Uso:
    python manage.py eliminar_paquete <id>
    python manage.py eliminar_paquete <id> --force
    python manage.py eliminar_paquete <id> --force --incluir-reservas
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError, Count
from apps.paquete.models import Paquete, SalidaPaquete, PaqueteServicio
from apps.reserva.models import Reserva


class Command(BaseCommand):
    help = 'Elimina un paquete por su ID, mostrando las relaciones afectadas'

    def add_arguments(self, parser):
        parser.add_argument(
            'paquete_id',
            type=int,
            help='ID del paquete a eliminar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Eliminar sin pedir confirmación (para relaciones CASCADE)'
        )
        parser.add_argument(
            '--incluir-reservas',
            action='store_true',
            help='También eliminar las reservas asociadas (PELIGROSO)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular la eliminación sin ejecutarla'
        )

    def handle(self, *args, **options):
        paquete_id = options['paquete_id']
        force = options['force']
        incluir_reservas = options['incluir_reservas']
        dry_run = options['dry_run']

        # Buscar el paquete
        try:
            paquete = Paquete.objects.get(id=paquete_id)
        except Paquete.DoesNotExist:
            raise CommandError(f'El paquete con ID {paquete_id} no existe.')

        # Analizar relaciones
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING(f'PAQUETE ID: {paquete.id}'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Nombre: {paquete.nombre}')
        self.stdout.write(f'Activo: {"Sí" if paquete.activo else "No"}')
        self.stdout.write(f'Tipo: {paquete.tipo_paquete.nombre if paquete.tipo_paquete else "N/A"}')
        self.stdout.write(f'Destino: {paquete.destino.ciudad.nombre if paquete.destino else "N/A"}')

        # Contar relaciones
        num_salidas = SalidaPaquete.objects.filter(paquete=paquete).count()
        num_servicios = PaqueteServicio.objects.filter(paquete=paquete).count()
        num_reservas = Reserva.objects.filter(paquete=paquete).count()

        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('RELACIONES:')
        self.stdout.write('-' * 60)
        self.stdout.write(f'  Salidas: {num_salidas} (CASCADE)')
        self.stdout.write(f'  Servicios: {num_servicios} (CASCADE)')
        self.stdout.write(f'  Reservas: {num_reservas} (PROTECT)')

        # Determinar tipo de eliminación
        tiene_reservas = num_reservas > 0
        tiene_cascade = num_salidas > 0 or num_servicios > 0

        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('ANÁLISIS:')
        self.stdout.write('-' * 60)

        if tiene_reservas:
            self.stdout.write(self.style.ERROR(
                f'❌ Este paquete tiene {num_reservas} reserva(s) asociada(s).'
            ))
            self.stdout.write(self.style.ERROR(
                '   No se puede eliminar sin eliminar primero las reservas.'
            ))

            if not incluir_reservas:
                self.stdout.write('\n' + self.style.WARNING(
                    'Opciones:'
                ))
                self.stdout.write('  1. Usa --incluir-reservas para eliminar también las reservas')
                self.stdout.write('  2. Reasigna las reservas a otro paquete manualmente')
                self.stdout.write('  3. Desactiva el paquete en lugar de eliminarlo\n')

                if not force:
                    return
            else:
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  Se eliminarán {num_reservas} reserva(s) junto con el paquete.'
                ))
        elif tiene_cascade:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Se eliminarán automáticamente:'
            ))
            if num_salidas > 0:
                self.stdout.write(f'   - {num_salidas} salida(s)')
            if num_servicios > 0:
                self.stdout.write(f'   - {num_servicios} servicio(s)')
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ El paquete no tiene relaciones. Eliminación directa.'
            ))

        # Confirmar eliminación
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING(
                '🔍 MODO DRY-RUN: No se realizará ninguna eliminación.'
            ))
            self._simular_eliminacion(paquete, incluir_reservas)
            return

        if not force:
            self.stdout.write('')
            confirmacion = input('¿Confirmar eliminación? (escribir "ELIMINAR" para confirmar): ')
            if confirmacion != 'ELIMINAR':
                self.stdout.write(self.style.ERROR('\nOperación cancelada.'))
                return

        # Ejecutar eliminación
        self._ejecutar_eliminacion(paquete, incluir_reservas, num_reservas)

    def _simular_eliminacion(self, paquete, incluir_reservas):
        """Simula la eliminación y muestra qué se eliminaría."""
        self.stdout.write('\nSimulando eliminación...\n')

        try:
            with transaction.atomic():
                if incluir_reservas:
                    reservas = Reserva.objects.filter(paquete=paquete)
                    count_reservas = reservas.count()
                    if count_reservas > 0:
                        self.stdout.write(f'  Se eliminarían {count_reservas} reserva(s)')

                # Simular delete del paquete
                deleted_count, deleted_objects = paquete.delete()

                self.stdout.write(f'\nTotal de objetos a eliminar: {deleted_count}')
                for model, count in deleted_objects.items():
                    self.stdout.write(f'  - {model}: {count}')

                # Rollback
                raise Exception('Rollback intencional')

        except ProtectedError as e:
            self.stdout.write(self.style.ERROR(
                f'\n❌ No se puede eliminar: hay {len(e.protected_objects)} objeto(s) protegido(s)'
            ))
        except Exception as e:
            if 'Rollback intencional' in str(e):
                self.stdout.write(self.style.SUCCESS('\n✅ Simulación completada.'))
            else:
                self.stdout.write(self.style.ERROR(f'\nError: {e}'))

    def _ejecutar_eliminacion(self, paquete, incluir_reservas, num_reservas):
        """Ejecuta la eliminación real."""
        self.stdout.write('\nEjecutando eliminación...\n')

        try:
            with transaction.atomic():
                # Si hay que eliminar reservas primero
                if incluir_reservas and num_reservas > 0:
                    reservas_eliminadas, _ = Reserva.objects.filter(paquete=paquete).delete()
                    self.stdout.write(self.style.WARNING(
                        f'  ⚠️  Eliminadas {reservas_eliminadas} reserva(s)'
                    ))

                # Eliminar paquete
                nombre_paquete = paquete.nombre
                deleted_count, deleted_objects = paquete.delete()

                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Paquete "{nombre_paquete}" (ID: {paquete.id}) eliminado correctamente.'
                ))
                self.stdout.write(f'\nObjetos eliminados: {deleted_count}')
                for model, count in deleted_objects.items():
                    self.stdout.write(f'  - {model}: {count}')

        except ProtectedError as e:
            self.stdout.write(self.style.ERROR(
                f'\n❌ Error: No se puede eliminar el paquete.'
            ))
            self.stdout.write(self.style.ERROR(
                f'   Hay {len(e.protected_objects)} objeto(s) que protegen la eliminación.'
            ))
            self.stdout.write('\nUsa --incluir-reservas para forzar la eliminación.')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error inesperado: {e}'))
