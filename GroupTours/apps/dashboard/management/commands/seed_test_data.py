# apps/dashboard/management/commands/seed_test_data.py
"""
Management command para poblar SOLO Paquetes y Reservas usando Factory Boy

Uso:
    python manage.py seed_test_data
    python manage.py seed_test_data --paquetes 20 --reservas 100
    python manage.py seed_test_data --clean
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal


class Command(BaseCommand):
    help = 'Poblar base de datos con Paquetes y Reservas usando Factory Boy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paquetes',
            type=int,
            default=10,
            help='Cantidad de paquetes a crear (default: 10)'
        )
        parser.add_argument(
            '--reservas',
            type=int,
            default=50,
            help='Cantidad de reservas a crear (default: 50)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Limpiar paquetes y reservas antes de crear'
        )
        parser.add_argument(
            '--no-salidas',
            action='store_true',
            help='No crear salidas para los paquetes'
        )

    def handle(self, *args, **options):
        # Importar factories aquí para evitar problemas de importación circular
        from apps.paquete.factories import PaqueteFactory, SalidaPaqueteFactory
        from apps.reserva.factories import ReservaFactory, PasajeroFactory
        from apps.paquete.models import Paquete, SalidaPaquete
        from apps.reserva.models import Reserva, Pasajero
        
        cantidad_paquetes = options['paquetes']
        cantidad_reservas = options['reservas']
        clean = options['clean']
        crear_salidas = not options['no_salidas']

        self.stdout.write("="*70)
        self.stdout.write(self.style.SUCCESS("🌱 POBLAR DATOS DE TEST CON FACTORY BOY"))
        self.stdout.write("="*70)

        # PASO 1: Limpiar datos si se solicita
        if clean:
            self.stdout.write("\n🧹 Limpiando datos existentes...")
            with transaction.atomic():
                count_reservas = Reserva.objects.count()
                count_pasajeros = Pasajero.objects.count()
                count_paquetes = Paquete.objects.count()
                count_salidas = SalidaPaquete.objects.count()
                
                # Eliminar en orden (por FKs)
                Pasajero.objects.all().delete()
                Reserva.objects.all().delete()
                SalidaPaquete.objects.all().delete()
                Paquete.objects.all().delete()
                
                self.stdout.write(self.style.WARNING(
                    f"   ❌ Eliminados: {count_pasajeros} pasajeros, "
                    f"{count_reservas} reservas, "
                    f"{count_salidas} salidas, "
                    f"{count_paquetes} paquetes"
                ))

        # PASO 2: Verificar datos maestros necesarios
        self.stdout.write("\n📋 Verificando datos maestros...")
        
        from apps.tipo_paquete.models import TipoPaquete
        from apps.destino.models import Destino
        from apps.moneda.models import Moneda
        from apps.hotel.models import Hotel
        
        tipos = TipoPaquete.objects.count()
        destinos = Destino.objects.count()
        monedas = Moneda.objects.count()
        hoteles = Hotel.objects.count()
        
        if tipos == 0 or destinos == 0 or monedas == 0 or hoteles == 0:
            self.stdout.write(self.style.ERROR(
                "\n❌ ERROR: Faltan datos maestros necesarios."
            ))
            self.stdout.write(self.style.WARNING(
                "   Ejecuta primero: python manage.py populate_database"
            ))
            self.stdout.write(self.style.WARNING(
                "   O crea los datos maestros básicos (tipos, destinos, monedas, hoteles)"
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f"   ✅ {tipos} tipos, {destinos} destinos, "
            f"{monedas} monedas, {hoteles} hoteles"
        ))

        # PASO 3: Crear Paquetes
        self.stdout.write(f"\n📦 Creando {cantidad_paquetes} paquetes...")
        
        try:
            with transaction.atomic():
                if crear_salidas:
                    # Crear paquetes con salidas automáticas
                    paquetes = PaqueteFactory.create_batch(
                        cantidad_paquetes,
                        crear_salidas=2  # 2 salidas por paquete
                    )
                else:
                    # Crear paquetes sin salidas
                    paquetes = PaqueteFactory.create_batch(
                        cantidad_paquetes,
                        crear_salidas=0
                    )
                
                self.stdout.write(self.style.SUCCESS(
                    f"   ✅ {len(paquetes)} paquetes creados"
                ))
                
                # Mostrar muestra
                self.stdout.write("\n   🔍 Muestra de paquetes creados:")
                for i, paquete in enumerate(paquetes[:5], 1):
                    salidas_count = paquete.salidas.count()
                    self.stdout.write(
                        f"      {i}. {paquete.nombre} ({salidas_count} salidas)"
                    )
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error al crear paquetes: {e}"))
            import traceback
            traceback.print_exc()
            return

        # PASO 4: Verificar que hay salidas con cupos
        salidas_con_cupo = SalidaPaquete.objects.filter(
            cupo__gt=0,
            activo=True
        ).count()
        
        if salidas_con_cupo == 0:
            self.stdout.write(self.style.ERROR(
                "\n❌ ERROR: No hay salidas con cupo disponible."
            ))
            self.stdout.write(self.style.WARNING(
                "   No se pueden crear reservas sin salidas."
            ))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {salidas_con_cupo} salidas con cupo disponible"
        ))

        # PASO 5: Crear Reservas
        self.stdout.write(f"\n✈️  Creando {cantidad_reservas} reservas...")
        
        try:
            reservas_creadas = []
            errores = 0
            
            with transaction.atomic():
                for i in range(cantidad_reservas):
                    try:
                        # Crear reserva
                        reserva = ReservaFactory()
                        reservas_creadas.append(reserva)
                        
                        # Crear pasajero titular
                        PasajeroFactory(
                            reserva=reserva,
                            persona=reserva.titular,
                            es_titular=True
                        )
                        
                        # Crear pasajeros adicionales (si la reserva tiene más de 1 pasajero)
                        for j in range(reserva.cantidad_pasajeros - 1):
                            PasajeroFactory(reserva=reserva)
                        
                        # Progreso cada 10 reservas
                        if (i + 1) % 10 == 0:
                            self.stdout.write(
                                f"      Progreso: {i + 1}/{cantidad_reservas} reservas..."
                            )
                    
                    except Exception as e:
                        errores += 1
                        if errores <= 3:  # Mostrar solo primeros 3 errores
                            self.stdout.write(self.style.WARNING(
                                f"      ⚠️  Error en reserva {i+1}: {str(e)[:50]}..."
                            ))
                
                self.stdout.write(self.style.SUCCESS(
                    f"\n   ✅ {len(reservas_creadas)} reservas creadas"
                ))
                
                if errores > 0:
                    self.stdout.write(self.style.WARNING(
                        f"   ⚠️  {errores} errores (posiblemente por falta de cupos)"
                    ))
                
                # Mostrar muestra
                self.stdout.write("\n   🔍 Muestra de reservas creadas:")
                for i, reserva in enumerate(reservas_creadas[:5], 1):
                    pasajeros_count = reserva.pasajeros.count()
                    self.stdout.write(
                        f"      {i}. {reserva.codigo} - {reserva.titular} "
                        f"({pasajeros_count} pasajeros) - Gs {reserva.precio_unitario:,.0f}"
                    )
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error al crear reservas: {e}"))
            import traceback
            traceback.print_exc()
            return

        # PASO 6: Estadísticas finales
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("📊 ESTADÍSTICAS FINALES"))
        self.stdout.write("="*70)
        
        total_paquetes = Paquete.objects.count()
        total_salidas = SalidaPaquete.objects.count()
        total_reservas = Reserva.objects.count()
        total_pasajeros = Pasajero.objects.count()
        
        self.stdout.write(f"📦 Total Paquetes: {total_paquetes}")
        self.stdout.write(f"🚀 Total Salidas: {total_salidas}")
        self.stdout.write(f"✈️  Total Reservas: {total_reservas}")
        self.stdout.write(f"👥 Total Pasajeros: {total_pasajeros}")
        
        # Estadísticas por estado
        from django.db.models import Count
        estados = Reserva.objects.values('estado').annotate(total=Count('id'))
        
        self.stdout.write("\n📊 Reservas por estado:")
        for estado in estados:
            self.stdout.write(f"   {estado['estado']}: {estado['total']}")
        
        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.SUCCESS("✅ DATOS DE TEST CREADOS EXITOSAMENTE"))
        self.stdout.write("="*70)
        
        self.stdout.write("\n💡 TIPS:")
        self.stdout.write("   - Para limpiar y recrear: python manage.py seed_test_data --clean")
        self.stdout.write("   - Para más paquetes: python manage.py seed_test_data --paquetes 50")
        self.stdout.write("   - Para más reservas: python manage.py seed_test_data --reservas 200")

