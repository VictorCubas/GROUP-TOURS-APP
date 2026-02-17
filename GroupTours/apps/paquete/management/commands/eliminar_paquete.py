"""
Comando para eliminar paquetes de forma segura.

Uso:
    python manage.py eliminar_paquete <id>
    python manage.py eliminar_paquete <id> --force
    python manage.py eliminar_paquete <id> --force --incluir-reservas

Detecta automáticamente TODAS las relaciones en cadena:
- Paquete → SalidaPaquete → Reserva → FacturaElectronica, ComprobantePago, Voucher
- Y cualquier otra relación futura

Muestra un árbol completo de dependencias antes de eliminar.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.db.models.deletion import Collector
from apps.paquete.models import Paquete, SalidaPaquete


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
            '--eliminar-todo',
            action='store_true',
            help='Eliminar TODA la cadena: vouchers, comprobantes, facturas, reservas (MUY PELIGROSO)'
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
        eliminar_todo = options['eliminar_todo']
        dry_run = options['dry_run']

        # --eliminar-todo implica --incluir-reservas
        if eliminar_todo:
            incluir_reservas = True

        # Buscar el paquete
        try:
            paquete = Paquete.objects.get(id=paquete_id)
        except Paquete.DoesNotExist:
            raise CommandError(f'El paquete con ID {paquete_id} no existe.')

        # Mostrar info del paquete
        self._mostrar_info_paquete(paquete)

        # Analizar TODAS las relaciones automáticamente
        relaciones = self._analizar_relaciones(paquete)

        # Mostrar relaciones encontradas
        self._mostrar_relaciones(relaciones)

        # Determinar si se puede eliminar
        tiene_protect = relaciones['protect']['total'] > 0
        tiene_cascade = relaciones['cascade']['total'] > 0

        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('ANÁLISIS:')
        self.stdout.write('-' * 60)

        if tiene_protect:
            self._manejar_protect(relaciones, incluir_reservas, force)
            if not incluir_reservas:
                if not force:
                    return
        elif tiene_cascade:
            self.stdout.write(self.style.WARNING(
                f'⚠️  Se eliminarán {relaciones["cascade"]["total"]} objeto(s) en cascada'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '✅ El paquete no tiene relaciones. Eliminación directa.'
            ))

        # Modo dry-run
        if dry_run:
            self.stdout.write('\n' + self.style.WARNING(
                '🔍 MODO DRY-RUN: No se realizará ninguna eliminación.'
            ))
            self._simular_eliminacion(paquete, incluir_reservas, eliminar_todo)
            return

        # Confirmar eliminación
        if not force:
            self.stdout.write('')
            confirmacion = input('¿Confirmar eliminación? (escribir "ELIMINAR" para confirmar): ')
            if confirmacion != 'ELIMINAR':
                self.stdout.write(self.style.ERROR('\nOperación cancelada.'))
                return

        # Ejecutar eliminación
        self._ejecutar_eliminacion(paquete, incluir_reservas, eliminar_todo, relaciones)

    def _mostrar_info_paquete(self, paquete):
        """Muestra información básica del paquete."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.WARNING(f'PAQUETE ID: {paquete.id}'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Nombre: {paquete.nombre}')
        self.stdout.write(f'Activo: {"Sí" if paquete.activo else "No"}')
        self.stdout.write(f'Tipo: {paquete.tipo_paquete.nombre if paquete.tipo_paquete else "N/A"}')
        self.stdout.write(f'Destino: {paquete.destino.ciudad.nombre if paquete.destino else "N/A"}')

    def _analizar_relaciones(self, paquete):
        """
        Analiza TODAS las relaciones del paquete automáticamente.
        Incluye relaciones directas y anidadas (ej: Paquete → SalidaPaquete → Reserva)
        """
        relaciones = {
            'cascade': {'total': 0, 'detalle': []},
            'protect': {'total': 0, 'detalle': []},
            'set_null': {'total': 0, 'detalle': []},
            'set_default': {'total': 0, 'detalle': []},
        }

        # Analizar relaciones directas del Paquete
        self._analizar_modelo(paquete, relaciones, 'Paquete')

        # Analizar relaciones anidadas (SalidaPaquete)
        salidas = SalidaPaquete.objects.filter(paquete=paquete)
        for salida in salidas:
            self._analizar_modelo(salida, relaciones, f'SalidaPaquete(id={salida.id})')

        return relaciones

    def _analizar_modelo(self, instance, relaciones, origen):
        """Analiza las relaciones inversas de un modelo específico."""
        for rel in instance._meta.related_objects:
            accessor_name = rel.get_accessor_name()
            model_name = rel.related_model.__name__

            # Obtener on_delete
            on_delete_name = 'CASCADE'  # default
            if hasattr(rel, 'on_delete') and rel.on_delete:
                on_delete_name = rel.on_delete.__name__

            # Contar registros relacionados
            try:
                related_manager = getattr(instance, accessor_name)
                if hasattr(related_manager, 'count'):
                    count = related_manager.count()
                else:
                    count = 0
            except Exception:
                count = 0

            if count == 0:
                continue

            # Clasificar según on_delete
            tipo = on_delete_name.lower()
            if tipo not in relaciones:
                tipo = 'cascade'  # fallback

            relaciones[tipo]['total'] += count
            relaciones[tipo]['detalle'].append({
                'modelo': model_name,
                'origen': origen,
                'cantidad': count,
                'on_delete': on_delete_name,
            })

        return relaciones

    def _mostrar_relaciones(self, relaciones):
        """Muestra las relaciones encontradas."""
        self.stdout.write('\n' + '-' * 60)
        self.stdout.write('RELACIONES ENCONTRADAS:')
        self.stdout.write('-' * 60)

        total_general = sum(r['total'] for r in relaciones.values())

        if total_general == 0:
            self.stdout.write('  (ninguna)')
            return

        # CASCADE
        if relaciones['cascade']['total'] > 0:
            self.stdout.write(self.style.WARNING(
                f"\n  CASCADE ({relaciones['cascade']['total']} objetos):"
            ))
            for item in relaciones['cascade']['detalle']:
                self.stdout.write(
                    f"    - {item['modelo']}: {item['cantidad']} (desde {item['origen']})"
                )

        # PROTECT
        if relaciones['protect']['total'] > 0:
            self.stdout.write(self.style.ERROR(
                f"\n  PROTECT ({relaciones['protect']['total']} objetos) - BLOQUEAN ELIMINACIÓN:"
            ))
            for item in relaciones['protect']['detalle']:
                self.stdout.write(
                    f"    - {item['modelo']}: {item['cantidad']} (desde {item['origen']})"
                )

        # SET_NULL
        if relaciones['set_null']['total'] > 0:
            self.stdout.write(
                f"\n  SET_NULL ({relaciones['set_null']['total']} objetos):"
            )
            for item in relaciones['set_null']['detalle']:
                self.stdout.write(
                    f"    - {item['modelo']}: {item['cantidad']} (desde {item['origen']})"
                )

    def _manejar_protect(self, relaciones, incluir_reservas, force):
        """Maneja el caso de relaciones PROTECT."""
        total_protect = relaciones['protect']['total']

        self.stdout.write(self.style.ERROR(
            f'❌ Hay {total_protect} objeto(s) con PROTECT que bloquean la eliminación.'
        ))

        for item in relaciones['protect']['detalle']:
            self.stdout.write(self.style.ERROR(
                f"   - {item['cantidad']} {item['modelo']}(s) desde {item['origen']}"
            ))

        if not incluir_reservas:
            self.stdout.write('\n' + self.style.WARNING('Opciones:'))
            self.stdout.write('  1. Usa --incluir-reservas para eliminar también las reservas')
            self.stdout.write('  2. Reasigna las reservas a otro paquete/salida manualmente')
            self.stdout.write('  3. Desactiva el paquete en lugar de eliminarlo\n')
        else:
            self.stdout.write(self.style.WARNING(
                f'\n⚠️  Se eliminarán {total_protect} objeto(s) protegido(s).'
            ))

    def _simular_eliminacion(self, paquete, incluir_reservas, eliminar_todo):
        """
        Simula la eliminación mostrando qué se eliminaría.
        """
        self.stdout.write('\nSimulando eliminación...\n')

        from apps.reserva.models import Reserva

        total_objetos = 0
        resumen = {}

        # 1. Si eliminar_todo, contar dependencias de reservas
        if eliminar_todo:
            deps = self._contar_dependencias_reservas(paquete)
            if deps['total'] > 0:
                self.stdout.write(self.style.WARNING(
                    '  Dependencias de reservas a eliminar:'
                ))
                for modelo, cantidad in deps['detalle'].items():
                    self.stdout.write(f'    - {modelo}: {cantidad}')
                    resumen[modelo] = cantidad
                    total_objetos += cantidad

        # 2. Contar reservas
        if incluir_reservas:
            salidas_ids = list(
                SalidaPaquete.objects.filter(paquete=paquete).values_list('id', flat=True)
            )

            reservas_paquete = Reserva.objects.filter(paquete=paquete).count()
            reservas_salidas = Reserva.objects.filter(salida_id__in=salidas_ids).count()
            total_reservas = reservas_paquete + reservas_salidas

            if total_reservas > 0:
                self.stdout.write(f'  Reservas a eliminar: {total_reservas}')
                resumen['reserva.Reserva'] = total_reservas
                total_objetos += total_reservas

        # 3. Contar objetos CASCADE del paquete (manualmente para evitar ProtectedError)
        # Paquete
        resumen['paquete.Paquete'] = 1
        total_objetos += 1

        # Salidas y sus dependencias
        salidas = SalidaPaquete.objects.filter(paquete=paquete)
        num_salidas = salidas.count()
        if num_salidas > 0:
            resumen['paquete.SalidaPaquete'] = num_salidas
            total_objetos += num_salidas

            # Dependencias de salidas
            from apps.paquete.models import (
                CupoHabitacionSalida, HistorialPrecioPaquete,
                PrecioCatalogoHotel, PrecioCatalogoHabitacion,
                HistorialPrecioHabitacion
            )

            for modelo, nombre in [
                (CupoHabitacionSalida, 'paquete.CupoHabitacionSalida'),
                (HistorialPrecioPaquete, 'paquete.HistorialPrecioPaquete'),
                (HistorialPrecioHabitacion, 'paquete.HistorialPrecioHabitacion'),
                (PrecioCatalogoHotel, 'paquete.PrecioCatalogoHotel'),
                (PrecioCatalogoHabitacion, 'paquete.PrecioCatalogoHabitacion'),
            ]:
                try:
                    count = modelo.objects.filter(
                        salida__in=salidas
                    ).count()
                    if count > 0:
                        resumen[nombre] = count
                        total_objetos += count
                except Exception:
                    pass

        # Servicios del paquete
        from apps.paquete.models import PaqueteServicio
        num_servicios = PaqueteServicio.objects.filter(paquete=paquete).count()
        if num_servicios > 0:
            resumen['paquete.PaqueteServicio'] = num_servicios
            total_objetos += num_servicios

        # Mostrar resumen final
        self.stdout.write(f'\nTotal de objetos a eliminar: {total_objetos}')
        for modelo, cantidad in sorted(resumen.items()):
            self.stdout.write(f'  - {modelo}: {cantidad}')

        # Verificar si la eliminación real funcionaría
        if eliminar_todo and incluir_reservas:
            self.stdout.write(self.style.SUCCESS(
                '\n✅ Con --eliminar-todo, la eliminación debería funcionar.'
            ))
        elif incluir_reservas:
            deps = self._contar_dependencias_reservas(paquete)
            if deps['total'] > 0:
                self.stdout.write(self.style.WARNING(
                    '\n⚠️  Las reservas tienen dependencias. Usa --eliminar-todo.'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    '\n✅ La eliminación debería funcionar.'
                ))
        else:
            # Verificar si hay reservas (PROTECT)
            num_reservas = resumen.get('reserva.Reserva', 0)
            if num_reservas > 0:
                self.stdout.write(self.style.ERROR(
                    f'\n❌ Hay {num_reservas} reserva(s) que bloquean (PROTECT).'
                ))
                self.stdout.write('   Usa --incluir-reservas o --eliminar-todo.')
            else:
                self.stdout.write(self.style.SUCCESS(
                    '\n✅ La eliminación debería funcionar.'
                ))

    def _contar_dependencias_reservas(self, paquete):
        """Cuenta las dependencias de las reservas sin eliminarlas."""
        from apps.reserva.models import Reserva

        salidas_ids = list(
            SalidaPaquete.objects.filter(paquete=paquete).values_list('id', flat=True)
        )

        reservas_ids = list(
            Reserva.objects.filter(paquete=paquete).values_list('id', flat=True)
        ) + list(
            Reserva.objects.filter(salida_id__in=salidas_ids).values_list('id', flat=True)
        )
        reservas_ids = list(set(reservas_ids))

        resultado = {'total': 0, 'detalle': {}}

        if not reservas_ids:
            return resultado

        # Contar Vouchers
        try:
            from apps.comprobante.models import Voucher
            count = Voucher.objects.filter(reserva_id__in=reservas_ids).count()
            if count > 0:
                resultado['detalle']['comprobante.Voucher'] = count
                resultado['total'] += count
        except ImportError:
            pass

        # Contar ComprobantePago y sus distribuciones
        try:
            from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion

            comprobantes_ids = list(
                ComprobantePago.objects.filter(
                    reserva_id__in=reservas_ids
                ).values_list('id', flat=True)
            )

            count_comprobantes = len(comprobantes_ids)
            if count_comprobantes > 0:
                resultado['detalle']['comprobante.ComprobantePago'] = count_comprobantes
                resultado['total'] += count_comprobantes

                # Contar distribuciones
                count_dist = ComprobantePagoDistribucion.objects.filter(
                    comprobante_id__in=comprobantes_ids
                ).count()
                if count_dist > 0:
                    resultado['detalle']['comprobante.ComprobantePagoDistribucion'] = count_dist
                    resultado['total'] += count_dist
        except ImportError:
            pass

        # Contar FacturaElectronica
        try:
            from apps.facturacion.models import FacturaElectronica
            count = FacturaElectronica.objects.filter(reserva_id__in=reservas_ids).count()
            if count > 0:
                resultado['detalle']['facturacion.FacturaElectronica'] = count
                resultado['total'] += count
        except ImportError:
            pass

        return resultado

    def _ejecutar_eliminacion(self, paquete, incluir_reservas, eliminar_todo, relaciones):
        """Ejecuta la eliminación real."""
        self.stdout.write('\nEjecutando eliminación...\n')

        try:
            with transaction.atomic():
                # Si hay que eliminar reservas primero
                if incluir_reservas and relaciones['protect']['total'] > 0:
                    from apps.reserva.models import Reserva

                    # Obtener todas las reservas relacionadas
                    salidas_ids = SalidaPaquete.objects.filter(
                        paquete=paquete
                    ).values_list('id', flat=True)

                    # Si eliminar_todo, eliminar dependencias primero
                    if eliminar_todo:
                        self._eliminar_dependencias_reservas(paquete, list(salidas_ids))

                    # Ahora eliminar las reservas
                    reservas_paquete = Reserva.objects.filter(paquete=paquete)
                    reservas_salidas = Reserva.objects.filter(salida_id__in=salidas_ids)

                    count_paquete = reservas_paquete.count()
                    count_salidas = reservas_salidas.count()

                    reservas_paquete.delete()
                    reservas_salidas.delete()

                    total_reservas = count_paquete + count_salidas
                    if total_reservas > 0:
                        self.stdout.write(self.style.WARNING(
                            f'  ⚠️  Eliminadas {total_reservas} reserva(s)'
                        ))

                # Eliminar paquete
                nombre_paquete = paquete.nombre
                paquete_id = paquete.id
                deleted_count, deleted_objects = paquete.delete()

                self.stdout.write(self.style.SUCCESS(
                    f'\n✅ Paquete "{nombre_paquete}" (ID: {paquete_id}) eliminado correctamente.'
                ))
                self.stdout.write(f'\nObjetos eliminados: {deleted_count}')
                for model, count in deleted_objects.items():
                    self.stdout.write(f'  - {model}: {count}')

        except ProtectedError as e:
            protected_models = {}
            for obj in e.protected_objects:
                model_name = obj._meta.label
                protected_models[model_name] = protected_models.get(model_name, 0) + 1

            self.stdout.write(self.style.ERROR(
                '\n❌ Error: No se puede eliminar el paquete.'
            ))
            self.stdout.write(self.style.ERROR('   Modelos que bloquean:'))
            for model_name, count in protected_models.items():
                self.stdout.write(self.style.ERROR(f'     - {model_name}: {count}'))

            if not eliminar_todo:
                self.stdout.write(
                    '\n   Usa --eliminar-todo para eliminar toda la cadena de dependencias.'
                )
            else:
                self.stdout.write(
                    '\n   Hay dependencias adicionales. Revisa los modelos bloqueantes.'
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error inesperado: {e}'))

    def _eliminar_dependencias_reservas(self, paquete, salidas_ids):
        """
        Elimina las dependencias de las reservas (facturas, pagos, vouchers).
        Esto permite que luego se puedan eliminar las reservas.

        Cadena de dependencias:
        - Reserva → ComprobantePago → ComprobantePagoDistribucion
        - Reserva → Voucher
        - Reserva → FacturaElectronica
        """
        from apps.reserva.models import Reserva

        # Obtener IDs de todas las reservas
        reservas_paquete_ids = list(
            Reserva.objects.filter(paquete=paquete).values_list('id', flat=True)
        )
        reservas_salidas_ids = list(
            Reserva.objects.filter(salida_id__in=salidas_ids).values_list('id', flat=True)
        )
        todas_reservas_ids = list(set(reservas_paquete_ids + reservas_salidas_ids))

        if not todas_reservas_ids:
            return

        self.stdout.write('  Eliminando dependencias de reservas...')

        # 1. Eliminar ComprobantePagoDistribucion (depende de ComprobantePago)
        try:
            from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion

            # Obtener IDs de comprobantes relacionados a las reservas
            comprobantes_ids = list(
                ComprobantePago.objects.filter(
                    reserva_id__in=todas_reservas_ids
                ).values_list('id', flat=True)
            )

            if comprobantes_ids:
                # Eliminar distribuciones de esos comprobantes
                deleted, _ = ComprobantePagoDistribucion.objects.filter(
                    comprobante_id__in=comprobantes_ids
                ).delete()
                if deleted:
                    self.stdout.write(self.style.WARNING(
                        f'    ⚠️  Eliminadas {deleted} distribución(es) de pago'
                    ))

                # Eliminar los comprobantes
                deleted, _ = ComprobantePago.objects.filter(
                    id__in=comprobantes_ids
                ).delete()
                if deleted:
                    self.stdout.write(self.style.WARNING(
                        f'    ⚠️  Eliminados {deleted} comprobante(s) de pago'
                    ))
        except ImportError:
            pass

        # 2. Eliminar Vouchers
        try:
            from apps.comprobante.models import Voucher
            deleted, _ = Voucher.objects.filter(
                reserva_id__in=todas_reservas_ids
            ).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  Eliminados {deleted} voucher(s)'
                ))
        except ImportError:
            pass

        # 3. Eliminar FacturaElectronica
        try:
            from apps.facturacion.models import FacturaElectronica
            deleted, _ = FacturaElectronica.objects.filter(
                reserva_id__in=todas_reservas_ids
            ).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  Eliminadas {deleted} factura(s)'
                ))
        except ImportError:
            pass
