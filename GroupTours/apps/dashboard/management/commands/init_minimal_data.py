# apps/dashboard/management/commands/init_minimal_data.py
"""
Crear datos maestros MÍNIMOS necesarios para seed_test_data

Uso:
    python manage.py init_minimal_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Crear datos maestros mínimos para seed_test_data'

    def handle(self, *args, **options):
        self.stdout.write("="*70)
        self.stdout.write(self.style.SUCCESS("🚀 INICIALIZAR DATOS MÍNIMOS"))
        self.stdout.write("="*70)
        
        try:
            with transaction.atomic():
                # 1. Tipo de Documento
                self._crear_tipos_documento()
                
                # 2. Nacionalidades
                self._crear_nacionalidades()
                
                # 3. Monedas
                self._crear_monedas()
                
                # 4. Tipo de Paquete
                self._crear_tipos_paquete()
                
                # 5. Zona Geográfica y Ciudad
                self._crear_zonas_ciudades()
                
                # 6. Destinos
                self._crear_destinos()
                
                # 7. Hoteles y Habitaciones
                self._crear_hoteles()
                
                self.stdout.write("\n" + "="*70)
                self.stdout.write(self.style.SUCCESS("✅ DATOS MÍNIMOS CREADOS"))
                self.stdout.write("="*70)
                self.stdout.write("\n💡 Ahora puedes ejecutar:")
                self.stdout.write("   python manage.py seed_test_data --paquetes 20 --reservas 100")
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))
            import traceback
            traceback.print_exc()
    
    def _crear_tipos_documento(self):
        """Crear tipos de documento básicos"""
        from apps.tipo_documento.models import TipoDocumento
        
        tipos = [
            ('CI', 'Cédula de Identidad', 'Paraguay'),
            ('PASAPORTE', 'Pasaporte', 'Internacional'),
        ]
        
        created = 0
        for codigo, nombre, pais in tipos:
            _, was_created = TipoDocumento.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'pais': pais}
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {TipoDocumento.objects.count()} Tipos de Documento ({created} nuevos)")
    
    def _crear_nacionalidades(self):
        """Crear nacionalidades básicas"""
        from apps.nacionalidad.models import Nacionalidad
        
        nacionalidades = [
            ('PY', 'Paraguaya', 'PRY'),
            ('AR', 'Argentina', 'ARG'),
            ('BR', 'Brasileña', 'BRA'),
            ('US', 'Estadounidense', 'USA'),
        ]
        
        created = 0
        for alpha2, nombre, alpha3 in nacionalidades:
            _, was_created = Nacionalidad.objects.get_or_create(
                codigo_alpha2=alpha2,
                defaults={'nombre': nombre, 'codigo_alpha3': alpha3}
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {Nacionalidad.objects.count()} Nacionalidades ({created} nuevas)")
    
    def _crear_monedas(self):
        """Crear monedas básicas"""
        from apps.moneda.models import Moneda
        
        monedas = [
            ('USD', 'Dólar Estadounidense', '$', 2),
            ('PYG', 'Guaraní Paraguayo', 'Gs', 0),
        ]
        
        created = 0
        for codigo, nombre, simbolo, decimales in monedas:
            _, was_created = Moneda.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nombre': nombre,
                    'simbolo': simbolo,
                    'decimales': decimales
                }
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {Moneda.objects.count()} Monedas ({created} nuevas)")
    
    def _crear_tipos_paquete(self):
        """Crear tipos de paquete"""
        from apps.tipo_paquete.models import TipoPaquete
        
        tipos = [
            ('Aéreo', 'Paquete con vuelo incluido'),
            ('Terrestre', 'Paquete sin vuelo'),
        ]
        
        created = 0
        for nombre, descripcion in tipos:
            _, was_created = TipoPaquete.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {TipoPaquete.objects.count()} Tipos de Paquete ({created} nuevos)")
    
    def _crear_zonas_ciudades(self):
        """Crear zonas geográficas y ciudades básicas"""
        from apps.zona_geografica.models import ZonaGeografica
        from apps.ciudad.models import Ciudad
        
        # Zonas
        zona_sa, _ = ZonaGeografica.objects.get_or_create(
            nombre='Sudamérica',
            defaults={'descripcion': 'América del Sur'}
        )
        
        zona_na, _ = ZonaGeografica.objects.get_or_create(
            nombre='Norteamérica',
            defaults={'descripcion': 'América del Norte'}
        )
        
        # Ciudades
        ciudades = [
            ('Asunción', 'Paraguay', zona_sa),
            ('Buenos Aires', 'Argentina', zona_sa),
            ('Río de Janeiro', 'Brasil', zona_sa),
            ('Miami', 'Estados Unidos', zona_na),
        ]
        
        created = 0
        for nombre, pais, zona in ciudades:
            _, was_created = Ciudad.objects.get_or_create(
                nombre=nombre,
                defaults={'pais': pais, 'zona_geografica': zona}
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {Ciudad.objects.count()} Ciudades ({created} nuevas)")
    
    def _crear_destinos(self):
        """Crear destinos básicos"""
        from apps.destino.models import Destino
        from apps.ciudad.models import Ciudad
        
        ciudades = Ciudad.objects.all()[:4]
        
        created = 0
        for ciudad in ciudades:
            _, was_created = Destino.objects.get_or_create(
                ciudad=ciudad,
                defaults={'descripcion': f'Destino en {ciudad.nombre}'}
            )
            if was_created:
                created += 1
        
        self.stdout.write(f"   ✅ {Destino.objects.count()} Destinos ({created} nuevos)")
    
    def _crear_hoteles(self):
        """Crear hoteles y habitaciones básicos"""
        from apps.hotel.models import CadenaHotelera, Hotel, Habitacion
        from apps.ciudad.models import Ciudad
        
        # Cadena hotelera
        cadena, _ = CadenaHotelera.objects.get_or_create(
            nombre='Test Hotels',
            defaults={'descripcion': 'Cadena de hoteles para testing'}
        )
        
        # Hoteles
        ciudades = Ciudad.objects.all()[:3]
        hoteles_created = 0
        habitaciones_created = 0
        
        for i, ciudad in enumerate(ciudades, 1):
            hotel, was_created = Hotel.objects.get_or_create(
                nombre=f'Hotel {ciudad.nombre}',
                defaults={
                    'cadena_hotelera': cadena,
                    'direccion': f'Calle Principal {i}00',
                    'telefono': f'+000 000 00{i}000',
                    'email': f'hotel{i}@example.com',
                    'ciudad': ciudad,
                    'estrellas': 4
                }
            )
            
            if was_created:
                hoteles_created += 1
                
                # Crear habitaciones para este hotel
                tipos_habitacion = ['simple', 'doble', 'triple', 'suite']
                
                for j, tipo in enumerate(tipos_habitacion, 1):
                    capacidad = {'simple': 1, 'doble': 2, 'triple': 3, 'suite': 4}[tipo]
                    precio_base = {'simple': 50, 'doble': 80, 'triple': 120, 'suite': 200}[tipo]
                    
                    habitacion, hab_created = Habitacion.objects.get_or_create(
                        hotel=hotel,
                        numero=f'{i}0{j}',
                        defaults={
                            'tipo': tipo,
                            'capacidad': capacidad,
                            'precio_base': Decimal(str(precio_base)),
                            'descripcion': f'Habitación {tipo} con capacidad para {capacidad}'
                        }
                    )
                    
                    if hab_created:
                        habitaciones_created += 1
        
        total_hoteles = Hotel.objects.count()
        total_habitaciones = Habitacion.objects.count()
        
        self.stdout.write(
            f"   ✅ {total_hoteles} Hoteles ({hoteles_created} nuevos) "
            f"y {total_habitaciones} Habitaciones ({habitaciones_created} nuevas)"
        )

