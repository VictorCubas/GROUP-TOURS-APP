"""
Management command para poblar la base de datos con datos dummy coherentes.

Uso:
    python manage.py populate_database

Opciones:
    --clear: Elimina todos los datos antes de poblar (¡CUIDADO!)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random
from faker import Faker

# Inicializar Faker con locale español
fake = Faker('es_ES')

# Importar todos los modelos necesarios
from apps.zona_geografica.models import ZonaGeografica
from apps.nacionalidad.models import Nacionalidad
from apps.ciudad.models import Ciudad
from apps.moneda.models import Moneda, CotizacionMoneda
from apps.tipo_documento.models import TipoDocumento
from apps.tipo_paquete.models import TipoPaquete
from apps.distribuidora.models import Distribuidora
from apps.servicio.models import Servicio
from apps.hotel.models import CadenaHotelera, Hotel, Habitacion
from apps.persona.models import PersonaFisica
from apps.tipo_remuneracion.models import TipoRemuneracion
from apps.puesto.models import Puesto
from apps.empleado.models import Empleado
from apps.rol.models import Rol
from apps.modulo.models import Modulo
from apps.permiso.models import Permiso
from apps.usuario.models import Usuario
from apps.destino.models import Destino
from apps.paquete.models import Paquete, PaqueteServicio, SalidaPaquete, Temporada, CupoHabitacionSalida
from apps.reserva.models import Reserva, Pasajero, ReservaServiciosAdicionales
from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
from apps.facturacion.models import (
    Empresa, Establecimiento, PuntoExpedicion, Timbrado,
    TipoImpuesto, SubtipoImpuesto, ClienteFacturacion, FacturaElectronica
)
from apps.arqueo_caja.models import AperturaCaja, MovimientoCaja, Caja, CierreCaja


class Command(BaseCommand):
    help = 'Poblar base de datos con datos dummy coherentes y realistas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina todos los datos antes de poblar (¡USAR CON PRECAUCIÓN!)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('⚠️  ADVERTENCIA: Se eliminarán TODOS los datos'))
            confirm = input('¿Está seguro? Escriba "SI" para confirmar: ')
            if confirm != 'SI':
                self.stdout.write(self.style.ERROR('Operación cancelada'))
                return
            self.clear_database()

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('🚀 INICIANDO POBLACIÓN DE BASE DE DATOS'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        
        try:
            # Nivel 1: Datos Maestros Base
            self.stdout.write('\n📦 NIVEL 1: Datos Maestros Base')
            self.crear_zonas_geograficas()
            self.crear_nacionalidades()
            self.crear_ciudades()
            self.crear_monedas()
            self.crear_cotizaciones()
            self.crear_tipos_documento()
            
            # Nivel 2: Servicios y Recursos
            self.stdout.write('\n📦 NIVEL 2: Servicios y Recursos')
            self.crear_tipos_paquete()
            self.crear_distribuidoras()
            self.crear_servicios()
            self.crear_cadenas_hoteleras()
            self.crear_hoteles_completos()
            self.crear_personas_fisicas()
            self.crear_tipos_remuneracion()
            self.crear_puestos()
            self.crear_empleados()
            
            # Nivel 3: Usuarios y Destinos
            self.stdout.write('\n📦 NIVEL 3: Usuarios y Destinos')
            self.crear_modulos()
            self.crear_permisos()
            self.crear_roles()
            self.crear_usuarios()
            self.crear_destinos()
            
            # Nivel 4: Paquetes
            self.stdout.write('\n📦 NIVEL 4: Paquetes y Salidas')
            self.crear_temporadas()
            self.crear_paquetes_con_salidas()
            
            # Nivel 5: Reservas
            self.stdout.write('\n📦 NIVEL 5: Reservas y Pasajeros')
            self.crear_reservas_completas()
            
            # Nivel 6: Comprobantes
            self.stdout.write('\n📦 NIVEL 6: Comprobantes de Pago')
            self.crear_comprobantes_pago()
            
            # Nivel 7: Facturación
            self.stdout.write('\n📦 NIVEL 7: Facturación y Arqueo')
            self.crear_empresa_facturacion()
            self.crear_arqueos_caja()
            
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.SUCCESS('✅ BASE DE DATOS POBLADA EXITOSAMENTE'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.mostrar_resumen()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR: {str(e)}'))
            import traceback
            traceback.print_exc()

    def clear_database(self):
        """Elimina todos los datos de las tablas (¡PELIGROSO!)"""
        self.stdout.write(self.style.WARNING('🗑️  Eliminando datos existentes...'))
        
        # Orden inverso de creación para respetar foreign keys
        MovimientoCaja.objects.all().delete()
        AperturaCaja.objects.all().delete()
        FacturaElectronica.objects.all().delete()
        ClienteFacturacion.objects.all().delete()
        ComprobantePagoDistribucion.objects.all().delete()
        ComprobantePago.objects.all().delete()
        ReservaServiciosAdicionales.objects.all().delete()
        Pasajero.objects.all().delete()
        Reserva.objects.all().delete()
        CupoHabitacionSalida.objects.all().delete()
        SalidaPaquete.objects.all().delete()
        PaqueteServicio.objects.all().delete()
        Paquete.objects.all().delete()
        Temporada.objects.all().delete()
        Destino.objects.all().delete()
        Usuario.objects.all().delete()
        Permiso.objects.all().delete()
        Rol.objects.all().delete()
        Modulo.objects.all().delete()
        Empleado.objects.all().delete()
        Habitacion.objects.all().delete()
        Hotel.objects.all().delete()
        CadenaHotelera.objects.all().delete()
        PersonaFisica.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('   ✓ Datos eliminados'))

    # ========================================================================
    # NIVEL 1: DATOS MAESTROS BASE
    # ========================================================================

    @transaction.atomic
    def crear_zonas_geograficas(self):
        """Crear zonas geográficas del mundo"""
        zonas = [
            'América del Sur',
            'América del Norte',
            'América Central',
            'Europa',
            'Asia',
            'Oceanía',
            'África'
        ]
        
        for nombre in zonas:
            ZonaGeografica.objects.get_or_create(nombre=nombre)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(zonas)} Zonas Geográficas creadas'))

    @transaction.atomic
    def crear_nacionalidades(self):
        """Crear países con sus zonas geográficas"""
        paises = [
            ('Paraguay', 'PY', 'América del Sur'),
            ('Argentina', 'AR', 'América del Sur'),
            ('Brasil', 'BR', 'América del Sur'),
            ('Uruguay', 'UY', 'América del Sur'),
            ('Chile', 'CL', 'América del Sur'),
            ('Estados Unidos', 'US', 'América del Norte'),
            ('México', 'MX', 'América del Norte'),
            ('España', 'ES', 'Europa'),
            ('Francia', 'FR', 'Europa'),
            ('Italia', 'IT', 'Europa'),
        ]
        
        for nombre, codigo, zona_nombre in paises:
            zona = ZonaGeografica.objects.get(nombre=zona_nombre)
            Nacionalidad.objects.get_or_create(
                nombre=nombre,
                codigo_alpha2=codigo,
                defaults={'zona_geografica': zona}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(paises)} Nacionalidades creadas'))

    @transaction.atomic
    def crear_ciudades(self):
        """Crear ciudades para cada país"""
        ciudades_data = {
            'Paraguay': ['Asunción', 'Ciudad del Este', 'Encarnación'],
            'Argentina': ['Buenos Aires', 'Mendoza', 'Bariloche', 'Córdoba'],
            'Brasil': ['Río de Janeiro', 'São Paulo', 'Florianópolis', 'Foz do Iguazú'],
            'Uruguay': ['Montevideo', 'Punta del Este', 'Colonia del Sacramento'],
            'Chile': ['Santiago', 'Viña del Mar', 'Valparaíso'],
            'Estados Unidos': ['Miami', 'Nueva York', 'Orlando', 'Las Vegas'],
            'México': ['Cancún', 'Playa del Carmen', 'Ciudad de México'],
            'España': ['Madrid', 'Barcelona', 'Sevilla'],
            'Francia': ['París', 'Niza', 'Lyon'],
            'Italia': ['Roma', 'Venecia', 'Milán'],
        }
        
        total = 0
        for pais_nombre, ciudades in ciudades_data.items():
            pais = Nacionalidad.objects.get(nombre=pais_nombre)
            for ciudad_nombre in ciudades:
                Ciudad.objects.get_or_create(
                    nombre=ciudad_nombre,
                    defaults={'pais': pais}
                )
                total += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {total} Ciudades creadas'))

    @transaction.atomic
    def crear_monedas(self):
        """Crear monedas principales"""
        monedas = [
            ('Guaraní', 'Gs', 'PYG'),
            ('Dólar Estadounidense', '$', 'USD'),
            ('Peso Argentino', '$', 'ARS'),
            ('Real Brasileño', 'R$', 'BRL'),
            ('Euro', '€', 'EUR'),
        ]
        
        for nombre, simbolo, codigo in monedas:
            Moneda.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'simbolo': simbolo}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(monedas)} Monedas creadas'))

    @transaction.atomic
    def crear_cotizaciones(self):
        """Crear cotizaciones históricas de monedas"""
        # Crear cotizaciones para los últimos 30 días y próximos 15 días
        moneda_usd = Moneda.objects.get(codigo='USD')
        moneda_ars = Moneda.objects.get(codigo='ARS')
        moneda_brl = Moneda.objects.get(codigo='BRL')
        moneda_eur = Moneda.objects.get(codigo='EUR')
        
        hoy = timezone.now().date()
        
        # Cotizaciones base
        cotizaciones_base = {
            'USD': 7300,
            'ARS': 8,
            'BRL': 1500,
            'EUR': 7800,
        }
        
        total = 0
        for dias in range(-30, 16):  # -30 días atrás hasta +15 días adelante
            fecha = hoy + timedelta(days=dias)
            
            for codigo, valor_base in cotizaciones_base.items():
                moneda = Moneda.objects.get(codigo=codigo)
                # Variar el valor ±2% para simular variación del mercado
                variacion = random.uniform(0.98, 1.02)
                valor = Decimal(str(valor_base * variacion))
                
                CotizacionMoneda.objects.get_or_create(
                    moneda=moneda,
                    fecha_vigencia=fecha,
                    defaults={'valor_en_guaranies': valor}
                )
                total += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {total} Cotizaciones creadas'))

    @transaction.atomic
    def crear_tipos_documento(self):
        """Crear tipos de documentos de identidad"""
        tipos = [
            'Cédula de Identidad',
            'RUC',
            'Pasaporte',
            'DNI',
            'Carnet de Extranjería'
        ]
        
        for nombre in tipos:
            TipoDocumento.objects.get_or_create(nombre=nombre)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(tipos)} Tipos de Documento creados'))

    # ========================================================================
    # NIVEL 2: SERVICIOS Y RECURSOS
    # ========================================================================

    @transaction.atomic
    def crear_tipos_paquete(self):
        """Crear tipos de paquetes turísticos"""
        tipos = [
            ('Aéreo', 'Paquetes con traslado aéreo incluido'),
            ('Terrestre', 'Paquetes con traslado terrestre (bus)'),
            ('Combinado', 'Paquetes con traslado aéreo y terrestre'),
        ]
        
        for nombre, descripcion in tipos:
            TipoPaquete.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(tipos)} Tipos de Paquete creados'))

    @transaction.atomic
    def crear_distribuidoras(self):
        """Crear distribuidoras (operadores turísticos)"""
        distribuidoras = [
            ('Andesmar Turismo', 'Operador turístico especializado en viajes terrestres', '+595 21 234-5678', 'ventas@andesmar.com.py'),
            ('CVC Travel', 'Agencia mayorista de viajes', '+595 21 345-6789', 'info@cvctravel.com.py'),
            ('Despegar Tours', 'Operador de paquetes aéreos', '+595 21 456-7890', 'operaciones@despegar.com.py'),
            ('Decameron Vacaciones', 'Cadena hotelera all-inclusive', '+595 21 567-8901', 'reservas@decameron.com'),
            ('Resort Directo', 'Operador de resorts de playa', '+595 21 678-9012', 'ventas@resortdirecto.com'),
        ]
        
        for nombre, descripcion, telefono, email in distribuidoras:
            Distribuidora.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': descripcion,
                    'telefono': telefono,
                    'email': email
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(distribuidoras)} Distribuidoras creadas'))

    @transaction.atomic
    def crear_servicios(self):
        """Crear servicios incluidos en paquetes y habitaciones"""
        moneda_usd = Moneda.objects.get(codigo='USD')
        
        servicios_paquete = [
            ('Pasaje aéreo ida y vuelta', 'Vuelo internacional clase económica', 450, 'paquete'),
            ('Traslado aeropuerto-hotel-aeropuerto', 'Traslado privado', 50, 'paquete'),
            ('Desayuno buffet', 'Desayuno americano completo', 0, 'paquete'),
            ('Cena buffet', 'Cena internacional', 0, 'paquete'),
            ('All Inclusive', 'Todo incluido: comidas, bebidas y snacks', 200, 'paquete'),
            ('Seguro de viaje básico', 'Cobertura médica básica', 80, 'paquete'),
            ('Asistencia al viajero 24/7', 'Asistencia telefónica permanente', 40, 'paquete'),
            ('Excursión city tour', 'Tour guiado por la ciudad', 60, 'paquete'),
            ('Guía turístico', 'Guía profesional de turismo', 100, 'paquete'),
        ]
        
        servicios_hotel = [
            ('WiFi gratuito', 'Internet de alta velocidad', 0, 'hotel'),
            ('Piscina', 'Piscina climatizada', 0, 'hotel'),
            ('Gimnasio', 'Gimnasio completamente equipado', 0, 'hotel'),
            ('Spa', 'Centro de bienestar y spa', 150, 'hotel'),
            ('Room service 24h', 'Servicio a la habitación', 0, 'hotel'),
            ('Estacionamiento', 'Parking gratuito', 0, 'hotel'),
        ]
        
        servicios_habitacion = [
            ('Aire acondicionado', 'Climatización individual', 0, 'habitacion'),
            ('TV por cable', 'Televisión con canales internacionales', 0, 'habitacion'),
            ('Minibar', 'Frigobar con bebidas', 0, 'habitacion'),
            ('Caja fuerte', 'Caja de seguridad', 0, 'habitacion'),
            ('Vista al mar', 'Habitación con vista panorámica', 50, 'habitacion'),
        ]
        
        total = 0
        for servicios in [servicios_paquete, servicios_hotel, servicios_habitacion]:
            for nombre, descripcion, precio, tipo in servicios:
                Servicio.objects.get_or_create(
                    nombre=nombre,
                    defaults={
                        'descripcion': descripcion,
                        'precio': Decimal(str(precio)),
                        'tipo': tipo
                    }
                )
                total += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {total} Servicios creados'))

    @transaction.atomic
    def crear_cadenas_hoteleras(self):
        """Crear cadenas hoteleras"""
        cadenas = [
            ('Copacabana Hotels', 'Cadena de hoteles de lujo en Brasil'),
            ('Fasano Group', 'Hoteles boutique de alta gama'),
            ('Alvear Hotels', 'Cadena argentina de hoteles 5 estrellas'),
            ('Faena', 'Hoteles de diseño y arte'),
            ('The Ritz-Carlton', 'Cadena internacional de lujo'),
            ('Fontainebleau', 'Resorts de playa premium'),
            ('Hard Rock Hotels', 'Hoteles temáticos de música'),
            ('Live Aqua', 'Resorts adults-only de lujo'),
        ]
        
        for nombre, descripcion in cadenas:
            CadenaHotelera.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(cadenas)} Cadenas Hoteleras creadas'))

    @transaction.atomic
    def crear_hoteles_completos(self):
        """Crear hoteles con sus habitaciones"""
        moneda_usd = Moneda.objects.get(codigo='USD')
        moneda_ars = Moneda.objects.get(codigo='ARS')
        
        # Datos: (nombre_hotel, estrellas, ciudad_nombre, cadena_nombre, moneda, habitaciones)
        hoteles_data = [
            # BRASIL - Río de Janeiro
            ('Copacabana Palace', 5, 'Río de Janeiro', 'Copacabana Hotels', 'USD', [
                ('101', 'suite', 4, 800),
                ('102', 'doble', 2, 400),
                ('201', 'single', 1, 250),
                ('202', 'doble', 2, 400),
                ('301', 'triple', 3, 550),
            ]),
            ('Fasano Rio', 5, 'Río de Janeiro', 'Fasano Group', 'USD', [
                ('501', 'suite', 3, 650),
                ('502', 'doble', 2, 380),
                ('601', 'doble', 2, 380),
            ]),
            
            # ARGENTINA - Buenos Aires
            ('Alvear Palace Hotel', 5, 'Buenos Aires', 'Alvear Hotels', 'USD', [
                ('101', 'suite', 4, 750),
                ('102', 'doble', 2, 350),
                ('201', 'doble', 2, 350),
                ('202', 'triple', 3, 500),
            ]),
            ('Faena Hotel', 5, 'Buenos Aires', 'Faena', 'USD', [
                ('301', 'suite', 3, 600),
                ('302', 'doble', 2, 400),
                ('401', 'doble', 2, 400),
            ]),
            
            # USA - Miami
            ('The Ritz-Carlton South Beach', 5, 'Miami', 'The Ritz-Carlton', 'USD', [
                ('1001', 'suite', 4, 1200),
                ('1002', 'doble', 2, 550),
                ('2001', 'doble', 2, 550),
            ]),
            ('Fontainebleau Miami Beach', 4, 'Miami', 'Fontainebleau', 'USD', [
                ('301', 'triple', 3, 450),
                ('302', 'doble', 2, 350),
                ('401', 'doble', 2, 350),
            ]),
            
            # MÉXICO - Cancún
            ('Hard Rock Hotel Cancún', 5, 'Cancún', 'Hard Rock Hotels', 'USD', [
                ('101', 'suite', 4, 800),
                ('102', 'doble', 2, 400),
                ('201', 'doble', 2, 400),
            ]),
            ('Live Aqua Beach Resort', 5, 'Cancún', 'Live Aqua', 'USD', [
                ('501', 'suite', 3, 650),
                ('502', 'doble', 2, 420),
            ]),
            
            # ARGENTINA - Bariloche
            ('Llao Llao Hotel & Resort', 5, 'Bariloche', None, 'ARS', [
                ('101', 'suite', 4, 350000),
                ('102', 'triple', 3, 250000),
                ('201', 'doble', 2, 180000),
            ]),
        ]
        
        total_hoteles = 0
        total_habitaciones = 0
        
        for hotel_nombre, estrellas, ciudad_nombre, cadena_nombre, moneda_codigo, habitaciones in hoteles_data:
            ciudad = Ciudad.objects.get(nombre=ciudad_nombre)
            moneda = Moneda.objects.get(codigo=moneda_codigo)
            cadena = CadenaHotelera.objects.get(nombre=cadena_nombre) if cadena_nombre else None
            
            hotel, created = Hotel.objects.get_or_create(
                nombre=hotel_nombre,
                ciudad=ciudad,
                defaults={
                    'estrellas': estrellas,
                    'cadena': cadena,
                    'direccion': f'Av. Principal {random.randint(100, 9999)}, {ciudad_nombre}'
                }
            )
            if created:
                total_hoteles += 1
            
            # Crear habitaciones para este hotel
            for numero, tipo, capacidad, precio_noche in habitaciones:
                Habitacion.objects.get_or_create(
                    hotel=hotel,
                    numero=numero,
                    defaults={
                        'tipo': tipo,
                        'capacidad': capacidad,
                        'precio_noche': Decimal(str(precio_noche)),
                        'moneda': moneda
                    }
                )
                total_habitaciones += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {total_hoteles} Hoteles y {total_habitaciones} Habitaciones creadas'))

    @transaction.atomic
    def crear_personas_fisicas(self):
        """Crear personas físicas para clientes y pasajeros"""
        tipo_ci = TipoDocumento.objects.get(nombre='Cédula de Identidad')
        tipo_dni = TipoDocumento.objects.get(nombre='DNI')
        tipo_pasaporte = TipoDocumento.objects.get(nombre='Pasaporte')
        
        nac_py = Nacionalidad.objects.get(codigo_alpha2='PY')
        nac_ar = Nacionalidad.objects.get(codigo_alpha2='AR')
        nac_br = Nacionalidad.objects.get(codigo_alpha2='BR')
        
        # (tipo_doc, documento, nombre, apellido, fecha_nac, sexo, nacionalidad, email, telefono)
        personas = [
            # Paraguayos
            (tipo_ci, '4123456', 'María', 'González', '1985-03-15', 'F', nac_py, 'maria.gonzalez@email.com', '+595 981 123456'),
            (tipo_ci, '3987654', 'Juan', 'Pérez', '1978-07-22', 'M', nac_py, 'juan.perez@email.com', '+595 981 234567'),
            (tipo_ci, '5234567', 'Ana', 'Martínez', '1990-11-05', 'F', nac_py, 'ana.martinez@email.com', '+595 981 345678'),
            (tipo_ci, '4567890', 'Carlos', 'López', '1982-09-18', 'M', nac_py, 'carlos.lopez@email.com', '+595 981 456789'),
            (tipo_ci, '5678901', 'Laura', 'Benítez', '1993-02-28', 'F', nac_py, 'laura.benitez@email.com', '+595 981 567890'),
            (tipo_ci, '4890123', 'Fernando', 'Villalba', '1987-06-12', 'M', nac_py, 'fernando.villalba@email.com', '+595 981 678901'),
            
            # Argentinos
            (tipo_dni, '35123456', 'Lucía', 'Fernández', '1988-04-12', 'F', nac_ar, 'lucia.fernandez@gmail.com', '+54 11 2345-6789'),
            (tipo_dni, '42567890', 'Roberto', 'Silva', '1995-06-20', 'M', nac_ar, 'roberto.silva@gmail.com', '+54 11 3456-7890'),
            (tipo_dni, '38901234', 'Sofía', 'Ramírez', '1991-08-15', 'F', nac_ar, 'sofia.ramirez@gmail.com', '+54 11 4567-8901'),
            
            # Brasileños
            (tipo_pasaporte, 'BR123456', 'Gabriela', 'Santos', '1986-08-30', 'F', nac_br, 'gabi.santos@gmail.com', '+55 21 98765-4321'),
            (tipo_pasaporte, 'BR789012', 'Ricardo', 'Oliveira', '1979-12-15', 'M', nac_br, 'ricardo.oliveira@gmail.com', '+55 21 87654-3210'),
            
            # Empleados adicionales
            (tipo_ci, '2345678', 'Patricia', 'Benítez', '1980-05-10', 'F', nac_py, 'patricia.benitez@grouptours.com', '+595 21 555-0001'),
            (tipo_ci, '3456789', 'Diego', 'Romero', '1992-09-22', 'M', nac_py, 'diego.romero@grouptours.com', '+595 21 555-0002'),
            (tipo_ci, '4234567', 'Sofía', 'Acosta', '1988-03-18', 'F', nac_py, 'sofia.acosta@grouptours.com', '+595 21 555-0003'),
            (tipo_ci, '3678901', 'Marcos', 'Villalba', '1990-07-05', 'M', nac_py, 'marcos.villalba@grouptours.com', '+595 21 555-0004'),
            (tipo_ci, '4890234', 'Carmen', 'Rodríguez', '1985-11-30', 'F', nac_py, 'carmen.rodriguez@grouptours.com', '+595 21 555-0005'),
        ]
        
        for tipo_doc, documento, nombre, apellido, fecha_nac, sexo, nacionalidad, email, telefono in personas:
            PersonaFisica.objects.get_or_create(
                documento=documento,
                defaults={
                    'tipo_documento': tipo_doc,
                    'nombre': nombre,
                    'apellido': apellido,
                    'fecha_nacimiento': fecha_nac,
                    'sexo': sexo,
                    'nacionalidad': nacionalidad,
                    'email': email,
                    'telefono': telefono,
                    'direccion': f'Calle Ejemplo {random.randint(100, 9999)}'
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(personas)} Personas Físicas creadas'))

    @transaction.atomic
    def crear_tipos_remuneracion(self):
        """Crear tipos de remuneración"""
        tipos = [
            'Salario Fijo',
            'Comisión por Venta',
            'Salario + Comisión',
        ]
        
        for nombre in tipos:
            TipoRemuneracion.objects.get_or_create(nombre=nombre)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(tipos)} Tipos de Remuneración creados'))

    @transaction.atomic
    def crear_puestos(self):
        """Crear puestos de trabajo"""
        puestos = [
            'Gerente General',
            'Vendedor',
            'Contador',
            'Atención al Cliente',
            'Administrador de Sistema',
        ]
        
        for nombre in puestos:
            Puesto.objects.get_or_create(nombre=nombre)
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(puestos)} Puestos creados'))

    @transaction.atomic
    def crear_empleados(self):
        """Crear empleados del sistema"""
        # (documento, puesto, tipo_remuneracion, salario, comision)
        empleados_data = [
            ('2345678', 'Gerente General', 'Salario Fijo', 8000000, 0),
            ('3456789', 'Vendedor', 'Salario + Comisión', 3500000, 5.00),
            ('4234567', 'Contador', 'Salario Fijo', 6000000, 0),
            ('3678901', 'Vendedor', 'Salario + Comisión', 3500000, 5.00),
            ('4890234', 'Atención al Cliente', 'Salario Fijo', 4500000, 0),
        ]
        
        for documento, puesto_nombre, tipo_rem_nombre, salario, comision in empleados_data:
            persona = PersonaFisica.objects.get(documento=documento)
            puesto = Puesto.objects.get(nombre=puesto_nombre)
            tipo_rem = TipoRemuneracion.objects.get(nombre=tipo_rem_nombre)
            
            Empleado.objects.get_or_create(
                persona=persona.persona_ptr,
                defaults={
                    'puesto': puesto,
                    'tipo_remuneracion': tipo_rem,
                    'salario': salario,
                    'porcentaje_comision': Decimal(str(comision)),
                    'fecha_ingreso': date.today() - timedelta(days=random.randint(90, 730))
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(empleados_data)} Empleados creados'))

    # ========================================================================
    # NIVEL 3: USUARIOS Y DESTINOS
    # ========================================================================

    @transaction.atomic
    def crear_modulos(self):
        """Crear módulos del sistema"""
        modulos = [
            ('Reservas', 'Gestión de reservas de paquetes'),
            ('Paquetes', 'Administración de paquetes turísticos'),
            ('Hoteles', 'Gestión de hoteles y habitaciones'),
            ('Comprobantes', 'Registro de comprobantes de pago'),
            ('Facturación', 'Emisión de facturas electrónicas'),
            ('Reportes', 'Generación de reportes y estadísticas'),
            ('Usuarios', 'Administración de usuarios del sistema'),
            ('Configuración', 'Configuración general del sistema'),
        ]
        
        for nombre, descripcion in modulos:
            Modulo.objects.get_or_create(
                nombre=nombre,
                defaults={'descripcion': descripcion}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(modulos)} Módulos creados'))

    @transaction.atomic
    def crear_permisos(self):
        """Crear permisos para cada módulo"""
        acciones = ['Ver', 'Crear', 'Editar', 'Eliminar', 'Exportar']
        modulos = Modulo.objects.all()
        
        total = 0
        creados = 0
        for modulo in modulos:
            for accion in acciones:
                nombre_permiso = f'{accion} {modulo.nombre}'
                
                # Buscar primero por nombre (que tiene restricción unique)
                permiso_existente = Permiso.objects.filter(nombre=nombre_permiso).first()
                
                if permiso_existente:
                    # Si existe pero con otro módulo, actualizar
                    if permiso_existente.modulo != modulo:
                        permiso_existente.modulo = modulo
                        permiso_existente.save()
                    total += 1
                else:
                    # Crear nuevo
                    Permiso.objects.create(
                        modulo=modulo,
                        nombre=nombre_permiso,
                        descripcion=f'Permite {accion.lower()} {modulo.nombre.lower()}'
                    )
                    total += 1
                    creados += 1
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {total} Permisos verificados ({creados} nuevos creados)'))

    @transaction.atomic
    def crear_roles(self):
        """Crear roles con sus permisos"""
        # Administrador: todos los permisos
        rol_admin, created = Rol.objects.get_or_create(
            nombre='Administrador',
            defaults={'descripcion': 'Acceso total al sistema'}
        )
        # Siempre actualizar permisos del admin
        rol_admin.permisos.set(Permiso.objects.all())
        
        # Vendedor: Reservas (todos), Paquetes (ver), Comprobantes (todos), Hoteles (ver)
        rol_vendedor, created = Rol.objects.get_or_create(
            nombre='Vendedor',
            defaults={'descripcion': 'Gestión de ventas y reservas'}
        )
        permisos_vendedor = Permiso.objects.filter(
            nombre__in=[
                'Ver Reservas', 'Crear Reservas', 'Editar Reservas', 'Exportar Reservas',
                'Ver Paquetes', 'Ver Hoteles',
                'Ver Comprobantes', 'Crear Comprobantes', 'Editar Comprobantes', 'Exportar Comprobantes'
            ]
        )
        rol_vendedor.permisos.set(permisos_vendedor)
        
        # Contador: Facturación (todos), Reportes (todos), Comprobantes (ver)
        rol_contador, created = Rol.objects.get_or_create(
            nombre='Contador',
            defaults={'descripcion': 'Gestión contable y financiera'}
        )
        permisos_contador = Permiso.objects.filter(
            nombre__icontains='Facturación'
        ) | Permiso.objects.filter(
            nombre__icontains='Reportes'
        ) | Permiso.objects.filter(
            nombre='Ver Comprobantes'
        )
        rol_contador.permisos.set(permisos_contador)
        
        # Supervisor: todos menos Configuración y Usuarios
        rol_supervisor, created = Rol.objects.get_or_create(
            nombre='Supervisor',
            defaults={'descripcion': 'Supervisión de operaciones'}
        )
        permisos_supervisor = Permiso.objects.exclude(
            modulo__nombre__in=['Configuración', 'Usuarios']
        )
        rol_supervisor.permisos.set(permisos_supervisor)
        
        self.stdout.write(self.style.SUCCESS('   ✓ 4 Roles configurados con permisos'))

    @transaction.atomic
    def crear_usuarios(self):
        """Crear usuarios del sistema"""
        # (documento, username, rol_nombre, password)
        usuarios_data = [
            ('2345678', 'admin', 'Administrador', 'admin123'),
            ('3456789', 'diego.romero', 'Vendedor', 'vendedor123'),
            ('4234567', 'sofia.acosta', 'Contador', 'contador123'),
            ('3678901', 'marcos.vendedor', 'Vendedor', 'vendedor123'),
            ('4890234', 'carmen.supervisor', 'Supervisor', 'supervisor123'),
        ]
        
        for documento, username, rol_nombre, password in usuarios_data:
            persona = PersonaFisica.objects.get(documento=documento)
            empleado = Empleado.objects.get(persona=persona.persona_ptr)
            rol = Rol.objects.get(nombre=rol_nombre)
            
            usuario, created = Usuario.objects.get_or_create(
                username=username,
                defaults={
                    'empleado': empleado,
                    'email': persona.email,
                    'first_name': persona.nombre,
                    'last_name': persona.apellido or '',
                    'is_staff': True,
                    'is_active': True,
                    'debe_cambiar_contrasenia': False
                }
            )
            
            if created:
                usuario.set_password(password)
                usuario.roles.add(rol)
                usuario.save()
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(usuarios_data)} Usuarios creados'))
        self.stdout.write(self.style.WARNING('   ⚠️  Credenciales de prueba:'))
        self.stdout.write(self.style.WARNING('      admin / admin123'))
        self.stdout.write(self.style.WARNING('      diego.romero / vendedor123'))

    @transaction.atomic
    def crear_destinos(self):
        """Crear destinos turísticos con sus hoteles"""
        # (ciudad_nombre, descripcion, hoteles_nombres)
        destinos_data = [
            ('Río de Janeiro', 'Ciudad maravillosa con playas icónicas', ['Copacabana Palace', 'Fasano Rio']),
            ('Buenos Aires', 'Capital del tango y la cultura', ['Alvear Palace Hotel', 'Faena Hotel']),
            ('Miami', 'Playa y diversión en Florida', ['The Ritz-Carlton South Beach', 'Fontainebleau Miami Beach']),
            ('Cancún', 'Paraíso caribeño mexicano', ['Hard Rock Hotel Cancún', 'Live Aqua Beach Resort']),
            ('Bariloche', 'Destino de montaña en la Patagonia', ['Llao Llao Hotel & Resort']),
        ]
        
        for ciudad_nombre, descripcion, hoteles_nombres in destinos_data:
            ciudad = Ciudad.objects.get(nombre=ciudad_nombre)
            destino, created = Destino.objects.get_or_create(
                ciudad=ciudad,
                defaults={'descripcion': descripcion}
            )
            
            # Asociar hoteles al destino
            for hotel_nombre in hoteles_nombres:
                try:
                    hotel = Hotel.objects.get(nombre=hotel_nombre)
                    destino.hoteles.add(hotel)
                except Hotel.DoesNotExist:
                    pass
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(destinos_data)} Destinos creados'))

    # ========================================================================
    # NIVEL 4: PAQUETES Y SALIDAS
    # ========================================================================

    @transaction.atomic
    def crear_temporadas(self):
        """Crear temporadas turísticas"""
        year = timezone.now().year
        
        temporadas = [
            ('Verano 2025', date(year, 1, 1), date(year, 3, 31)),
            ('Otoño 2025', date(year, 4, 1), date(year, 6, 30)),
            ('Invierno 2025', date(year, 7, 1), date(year, 9, 30)),
            ('Primavera 2025', date(year, 10, 1), date(year, 12, 31)),
        ]
        
        for nombre, inicio, fin in temporadas:
            Temporada.objects.get_or_create(
                nombre=nombre,
                defaults={'fecha_inicio': inicio, 'fecha_fin': fin}
            )
        
        self.stdout.write(self.style.SUCCESS(f'   ✓ {len(temporadas)} Temporadas creadas'))

    @transaction.atomic
    def crear_paquetes_con_salidas(self):
        """Crear paquetes turísticos con sus salidas"""
        moneda_usd = Moneda.objects.get(codigo='USD')
        moneda_ars = Moneda.objects.get(codigo='ARS')
        tipo_aereo = TipoPaquete.objects.get(nombre='Aéreo')
        tipo_terrestre = TipoPaquete.objects.get(nombre='Terrestre')
        
        # PAQUETE 1: Río de Janeiro All Inclusive
        self._crear_paquete_rio_janeiro()
        
        # PAQUETE 2: Buenos Aires Romántico
        self._crear_paquete_buenos_aires()
        
        # PAQUETE 3: Miami Beach Paradise (Distribuidora)
        self._crear_paquete_miami()
        
        # PAQUETE 4: Cancún Todo Incluido (Distribuidora)
        self._crear_paquete_cancun()
        
        # PAQUETE 5: Bariloche Invierno
        self._crear_paquete_bariloche()
        
        self.stdout.write(self.style.SUCCESS('   ✓ 5 Paquetes con salidas creados'))

    def _crear_paquete_rio_janeiro(self):
        """Crear paquete Río de Janeiro"""
        destino = Destino.objects.get(ciudad__nombre='Río de Janeiro')
        tipo = TipoPaquete.objects.get(nombre='Aéreo')
        moneda = Moneda.objects.get(codigo='USD')
        temporada = Temporada.objects.get(nombre='Verano 2025')
        
        paquete, created = Paquete.objects.get_or_create(
            nombre='Río de Janeiro All Inclusive 5 días',
            defaults={
                'tipo_paquete': tipo,
                'modalidad': 'flexible',
                'destino': destino,
                'moneda': moneda,
                'propio': True,
                'personalizado': False,
                'cantidad_pasajeros': 30
            }
        )
        
        if not created:
            return
        
        # Agregar servicios al paquete
        servicios = [
            ('Pasaje aéreo ida y vuelta', 450),
            ('Traslado aeropuerto-hotel-aeropuerto', 50),
            ('Desayuno buffet', 0),
            ('Seguro de viaje básico', 80),
            ('Excursión city tour', 60),
        ]
        
        for servicio_nombre, precio in servicios:
            servicio = Servicio.objects.get(nombre=servicio_nombre)
            PaqueteServicio.objects.create(
                paquete=paquete,
                servicio=servicio,
                precio=Decimal(str(precio))
            )
        
        # Crear salidas
        hoteles = [
            Hotel.objects.get(nombre='Copacabana Palace'),
            Hotel.objects.get(nombre='Fasano Rio')
        ]
        
        # Salida 1: Marzo
        salida1 = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 3, 15),
            fecha_regreso=date(2025, 3, 20),
            temporada=temporada,
            moneda=moneda,
            precio_actual=Decimal('1900'),
            precio_final=Decimal('4000'),
            ganancia=Decimal('15.00'),
            cupo=30,
            senia=Decimal('300')
        )
        salida1.hoteles.set(hoteles)
        salida1.calcular_precio_venta()
        
        # Crear cupos por habitación
        for hotel in hoteles:
            for habitacion in hotel.habitaciones.all():
                CupoHabitacionSalida.objects.create(
                    salida=salida1,
                    habitacion=habitacion,
                    cupo=3  # 3 habitaciones disponibles de cada tipo
                )
        
        # Salida 2: Junio
        salida2 = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 6, 10),
            fecha_regreso=date(2025, 6, 15),
            temporada=Temporada.objects.get(nombre='Otoño 2025'),
            moneda=moneda,
            precio_actual=Decimal('1900'),
            precio_final=Decimal('4000'),
            ganancia=Decimal('15.00'),
            cupo=30,
            senia=Decimal('300')
        )
        salida2.hoteles.set(hoteles)
        salida2.calcular_precio_venta()
        
        for hotel in hoteles:
            for habitacion in hotel.habitaciones.all():
                CupoHabitacionSalida.objects.create(
                    salida=salida2,
                    habitacion=habitacion,
                    cupo=3
                )

    def _crear_paquete_buenos_aires(self):
        """Crear paquete Buenos Aires"""
        destino = Destino.objects.get(ciudad__nombre='Buenos Aires')
        tipo = TipoPaquete.objects.get(nombre='Aéreo')
        moneda = Moneda.objects.get(codigo='USD')
        temporada = Temporada.objects.get(nombre='Otoño 2025')
        
        paquete, created = Paquete.objects.get_or_create(
            nombre='Buenos Aires Romántico 4 días',
            defaults={
                'tipo_paquete': tipo,
                'modalidad': 'flexible',
                'destino': destino,
                'moneda': moneda,
                'propio': True,
                'personalizado': False,
                'cantidad_pasajeros': 20
            }
        )
        
        if not created:
            return
        
        # Agregar servicios
        servicios = [
            ('Pasaje aéreo ida y vuelta', 350),
            ('Traslado aeropuerto-hotel-aeropuerto', 40),
            ('Desayuno buffet', 0),
        ]
        
        for servicio_nombre, precio in servicios:
            servicio = Servicio.objects.get(nombre=servicio_nombre)
            PaqueteServicio.objects.create(
                paquete=paquete,
                servicio=servicio,
                precio=Decimal(str(precio))
            )
        
        # Crear salida
        hoteles = [
            Hotel.objects.get(nombre='Alvear Palace Hotel'),
            Hotel.objects.get(nombre='Faena Hotel')
        ]
        
        salida = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 4, 20),
            fecha_regreso=date(2025, 4, 24),
            temporada=temporada,
            moneda=moneda,
            precio_actual=Decimal('1400'),
            precio_final=Decimal('2400'),
            ganancia=Decimal('18.00'),
            cupo=20,
            senia=Decimal('250')
        )
        salida.hoteles.set(hoteles)
        salida.calcular_precio_venta()
        
        for hotel in hoteles:
            for habitacion in hotel.habitaciones.all():
                CupoHabitacionSalida.objects.create(
                    salida=salida,
                    habitacion=habitacion,
                    cupo=2
                )

    def _crear_paquete_miami(self):
        """Crear paquete Miami (Distribuidora)"""
        destino = Destino.objects.get(ciudad__nombre='Miami')
        tipo = TipoPaquete.objects.get(nombre='Aéreo')
        moneda = Moneda.objects.get(codigo='USD')
        distribuidora = Distribuidora.objects.get(nombre='Despegar Tours')
        temporada = Temporada.objects.get(nombre='Invierno 2025')
        
        paquete, created = Paquete.objects.get_or_create(
            nombre='Miami Beach Paradise 7 días',
            defaults={
                'tipo_paquete': tipo,
                'modalidad': 'flexible',
                'destino': destino,
                'moneda': moneda,
                'propio': False,
                'distribuidora': distribuidora,
                'personalizado': False
            }
        )
        
        if not created:
            return
        
        hotel = Hotel.objects.get(nombre='The Ritz-Carlton South Beach')
        
        salida = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 7, 1),
            fecha_regreso=date(2025, 7, 8),
            temporada=temporada,
            moneda=moneda,
            precio_actual=Decimal('3850'),
            precio_final=Decimal('8400'),
            comision=Decimal('12.00'),
            senia=Decimal('500')
        )
        salida.hoteles.set([hotel])
        salida.calcular_precio_venta()
        
        # Crear cupos por habitación
        for habitacion in hotel.habitaciones.all():
            CupoHabitacionSalida.objects.create(
                salida=salida,
                habitacion=habitacion,
                cupo=3
            )

    def _crear_paquete_cancun(self):
        """Crear paquete Cancún (Distribuidora)"""
        destino = Destino.objects.get(ciudad__nombre='Cancún')
        tipo = TipoPaquete.objects.get(nombre='Aéreo')
        moneda = Moneda.objects.get(codigo='USD')
        distribuidora = Distribuidora.objects.get(nombre='Decameron Vacaciones')
        temporada = Temporada.objects.get(nombre='Invierno 2025')
        
        paquete, created = Paquete.objects.get_or_create(
            nombre='Cancún Todo Incluido 6 días',
            defaults={
                'tipo_paquete': tipo,
                'modalidad': 'fijo',
                'destino': destino,
                'moneda': moneda,
                'propio': False,
                'distribuidora': distribuidora,
                'personalizado': False
            }
        )
        
        if not created:
            return
        
        hotel = Hotel.objects.get(nombre='Hard Rock Hotel Cancún')
        
        salida = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 8, 15),
            fecha_regreso=date(2025, 8, 21),
            temporada=temporada,
            moneda=moneda,
            precio_actual=Decimal('2400'),
            precio_final=Decimal('4800'),
            comision=Decimal('10.00'),
            senia=Decimal('400')
        )
        salida.hoteles.set([hotel])
        salida.calcular_precio_venta()
        
        # Crear cupos por habitación
        for habitacion in hotel.habitaciones.all():
            CupoHabitacionSalida.objects.create(
                salida=salida,
                habitacion=habitacion,
                cupo=3
            )

    def _crear_paquete_bariloche(self):
        """Crear paquete Bariloche (Terrestre)"""
        destino = Destino.objects.get(ciudad__nombre='Bariloche')
        tipo = TipoPaquete.objects.get(nombre='Terrestre')
        moneda = Moneda.objects.get(codigo='ARS')
        temporada = Temporada.objects.get(nombre='Invierno 2025')
        
        paquete, created = Paquete.objects.get_or_create(
            nombre='Bariloche Invierno 5 días',
            defaults={
                'tipo_paquete': tipo,
                'modalidad': 'flexible',
                'destino': destino,
                'moneda': moneda,
                'propio': True,
                'personalizado': False,
                'cantidad_pasajeros': 45
            }
        )
        
        if not created:
            return
        
        hotel = Hotel.objects.get(nombre='Llao Llao Hotel & Resort')
        
        salida = SalidaPaquete.objects.create(
            paquete=paquete,
            fecha_salida=date(2025, 7, 20),
            fecha_regreso=date(2025, 7, 25),
            temporada=temporada,
            moneda=moneda,
            precio_actual=Decimal('900000'),
            precio_final=Decimal('1400000'),
            ganancia=Decimal('20.00'),
            cupo=45,
            senia=Decimal('50000')
        )
        salida.hoteles.set([hotel])
        salida.calcular_precio_venta()
        
        for habitacion in hotel.habitaciones.all():
            CupoHabitacionSalida.objects.create(
                salida=salida,
                habitacion=habitacion,
                cupo=5
            )

    # ========================================================================
    # NIVEL 5: RESERVAS Y PASAJEROS
    # ========================================================================

    @transaction.atomic
    def crear_reservas_completas(self):
        """Crear reservas con diferentes estados"""
        # Desactivar temporalmente las señales para evitar problemas
        self._crear_reserva_finalizada()
        self._crear_reserva_confirmada_incompleta()
        self._crear_reserva_confirmada_sin_datos_completos()
        self._crear_reserva_pendiente()
        self._crear_reserva_cancelada()
        self._crear_reserva_confirmada_completa()
        
        self.stdout.write(self.style.SUCCESS('   ✓ 6 Reservas con estados diversos creadas'))

    def _crear_reserva_finalizada(self):
        """RESERVA 1: RSV-2025-0001 - FINALIZADA"""
        titular = PersonaFisica.objects.get(documento='4123456')
        paquete = Paquete.objects.get(nombre='Río de Janeiro All Inclusive 5 días')
        salida = paquete.salidas.first()
        habitacion = Hotel.objects.get(nombre='Copacabana Palace').habitaciones.filter(tipo='doble').first()
        
        # Verificar si ya existe una reserva para este titular y paquete
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=2,
            precio_unitario=Decimal('2921'),
            estado='pendiente',
            datos_completos=False
        )
        
        # Crear pasajeros
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('2921')
        )
        
        pasajero2 = PersonaFisica.objects.get(documento='3987654')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero2,
            es_titular=False,
            precio_asignado=Decimal('2921')
        )
        
        # Nota: Los comprobantes y cambios de estado se harán en el siguiente nivel

    def _crear_reserva_confirmada_incompleta(self):
        """RESERVA 2: RSV-2025-0002 - CONFIRMADA INCOMPLETA"""
        titular = PersonaFisica.objects.get(documento='5234567')
        paquete = Paquete.objects.get(nombre='Buenos Aires Romántico 4 días')
        salida = paquete.salidas.first()
        habitacion = Hotel.objects.get(nombre='Faena Hotel').habitaciones.filter(tipo='doble').first()
        
        # Verificar si ya existe una reserva para este titular y paquete
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=2,
            precio_unitario=Decimal('2000'),
            estado='pendiente',
            datos_completos=False
        )
        
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('2000')
        )
        
        pasajero2 = PersonaFisica.objects.get(documento='4567890')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero2,
            es_titular=False,
            precio_asignado=Decimal('2000')
        )

    def _crear_reserva_confirmada_sin_datos_completos(self):
        """RESERVA 3: RSV-2025-0003 - CONFIRMADA SIN DATOS COMPLETOS"""
        titular = PersonaFisica.objects.get(documento='35123456')
        paquete = Paquete.objects.get(nombre='Miami Beach Paradise 7 días')
        salida = paquete.salidas.first()
        habitacion = Hotel.objects.get(nombre='The Ritz-Carlton South Beach').habitaciones.filter(tipo='suite').first()
        
        # Verificar si ya existe una reserva para este titular y paquete
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=4,
            precio_unitario=Decimal('4312'),
            estado='pendiente',
            datos_completos=False
        )
        
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('4312')
        )
        
        pasajero2 = PersonaFisica.objects.get(documento='42567890')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero2,
            es_titular=False,
            precio_asignado=Decimal('4312')
        )
        
        # Crear pasajeros por asignar (con datos reales usando Faker)
        tipo_ci = TipoDocumento.objects.get(nombre='Cédula de Identidad')
        nac_ar = Nacionalidad.objects.get(codigo_alpha2='AR')
        
        for i in range(2):
            # Generar persona con datos realistas
            nombre_fake = fake.first_name()
            apellido_fake = fake.last_name()
            
            persona_por_asignar = PersonaFisica.objects.create(
                tipo_documento=tipo_ci,
                documento=fake.unique.random_int(min=40000000 + i*1000, max=49999999),
                nombre=nombre_fake,
                apellido=apellido_fake,
                email=f'{nombre_fake.lower()}.{apellido_fake.lower()}@example.com',
                telefono=f'+595 {fake.random_int(900000000, 999999999)}',
                sexo=fake.random_element(['M', 'F']),
                fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=70),
                nacionalidad=nac_ar
            )
            
            Pasajero.objects.create(
                reserva=reserva,
                persona=persona_por_asignar,
                es_titular=False,
                por_asignar=True,  # Marcado como por asignar, pero con datos reales
                precio_asignado=Decimal('4312')
            )
        
        # Agregar servicio adicional
        servicio_excursion = Servicio.objects.create(
            nombre='Excursión a los Everglades',
            descripcion='Tour guiado al parque nacional',
            precio=Decimal('120'),
            tipo='paquete'
        )
        
        ReservaServiciosAdicionales.objects.create(
            reserva=reserva,
            servicio=servicio_excursion,
            cantidad=4,
            precio_unitario=Decimal('120'),
            observacion='Tour en español'
        )

    def _crear_reserva_pendiente(self):
        """RESERVA 4: RSV-2025-0004 - PENDIENTE"""
        titular = PersonaFisica.objects.get(documento='BR123456')
        paquete = Paquete.objects.get(nombre='Cancún Todo Incluido 6 días')
        salida = paquete.salidas.first()
        habitacion = Hotel.objects.get(nombre='Hard Rock Hotel Cancún').habitaciones.filter(tipo='doble').first()
        
        # Verificar si ya existe una reserva para este titular y paquete
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=2,
            precio_unitario=Decimal('2640'),
            estado='pendiente',
            datos_completos=False
        )
        
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('2640')
        )
        
        # Pasajero por asignar (con datos reales usando Faker)
        tipo_pasaporte = TipoDocumento.objects.get(nombre='Pasaporte')
        nac_br = Nacionalidad.objects.get(codigo_alpha2='BR')
        
        # Generar persona con datos realistas
        nombre_fake = fake.first_name_female()  # Femenino
        apellido_fake = fake.last_name()
        
        persona_por_asignar = PersonaFisica.objects.create(
            tipo_documento=tipo_pasaporte,
            documento=fake.unique.bothify(text='??######', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'),  # Formato pasaporte
            nombre=nombre_fake,
            apellido=apellido_fake,
            email=f'{nombre_fake.lower()}.{apellido_fake.lower()}@example.com',
            telefono=f'+55 {fake.random_int(10000000, 99999999)}',  # Formato Brasil
            sexo='F',
            fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=65),
            nacionalidad=nac_br
        )
        
        Pasajero.objects.create(
            reserva=reserva,
            persona=persona_por_asignar,
            es_titular=False,
            por_asignar=True,  # Marcado como por asignar, pero con datos reales
            precio_asignado=Decimal('2640')
        )

    def _crear_reserva_cancelada(self):
        """RESERVA 5: RSV-2025-0005 - CANCELADA"""
        titular = PersonaFisica.objects.get(documento='BR789012')
        paquete = Paquete.objects.get(nombre='Río de Janeiro All Inclusive 5 días')
        salida = paquete.salidas.all()[1]  # Segunda salida (junio)
        habitacion = Hotel.objects.get(nombre='Fasano Rio').habitaciones.filter(tipo='suite').first()
        
        # Verificar si ya existe una reserva para este titular y paquete
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=3,
            precio_unitario=Decimal('3500'),
            estado='cancelada',
            datos_completos=False,
            fecha_cancelacion=timezone.now() - timedelta(days=30),
            motivo_cancelacion_id='1',
            motivo_cancelacion='Cliente cambió de destino por razones familiares',
            cupos_liberados=True
        )
        
        # Crear pasajeros (aunque esté cancelada)
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('3500')
        )
        
        pasajero2 = PersonaFisica.objects.get(documento='4123456')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero2,
            es_titular=False,
            precio_asignado=Decimal('3500')
        )
        
        pasajero3 = PersonaFisica.objects.get(documento='3987654')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero3,
            es_titular=False,
            precio_asignado=Decimal('3500')
        )

    def _crear_reserva_confirmada_completa(self):
        """RESERVA 6: RSV-2025-0006 - CONFIRMADA COMPLETA (falta pagar saldo)"""
        titular = PersonaFisica.objects.get(documento='4123456')
        paquete = Paquete.objects.get(nombre='Bariloche Invierno 5 días')
        salida = paquete.salidas.first()
        habitacion = Hotel.objects.get(nombre='Llao Llao Hotel & Resort').habitaciones.filter(tipo='triple').first()
        
        # Verificar si ya existe una reserva para este titular, paquete y salida
        reserva = Reserva.objects.filter(
            titular=titular,
            paquete=paquete,
            salida=salida
        ).first()
        
        if reserva:
            return  # La reserva ya existe, no crear duplicado
        
        reserva = Reserva.objects.create(
            titular=titular,
            paquete=paquete,
            salida=salida,
            habitacion=habitacion,
            cantidad_pasajeros=3,
            precio_unitario=Decimal('250000'),
            estado='pendiente',
            datos_completos=False
        )
        
        Pasajero.objects.create(
            reserva=reserva,
            persona=titular,
            es_titular=True,
            precio_asignado=Decimal('250000')
        )
        
        pasajero2 = PersonaFisica.objects.get(documento='5234567')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero2,
            es_titular=False,
            precio_asignado=Decimal('250000')
        )
        
        pasajero3 = PersonaFisica.objects.get(documento='4567890')
        Pasajero.objects.create(
            reserva=reserva,
            persona=pasajero3,
            es_titular=False,
            precio_asignado=Decimal('250000')
        )

    # ========================================================================
    # NIVEL 6: COMPROBANTES DE PAGO
    # ========================================================================

    @transaction.atomic
    def crear_comprobantes_pago(self):
        """Crear comprobantes de pago para las reservas"""
        # Nota: La creación de comprobantes requiere tener aperturas de caja
        # Por ahora solo crearemos la estructura básica
        
        self.stdout.write(self.style.WARNING('   ⚠️  Comprobantes se crearán después de configurar arqueos de caja'))
        self.stdout.write(self.style.SUCCESS('   ✓ Estructura de comprobantes preparada'))

    # ========================================================================
    # NIVEL 7: FACTURACIÓN Y ARQUEO
    # ========================================================================

    @transaction.atomic
    def crear_empresa_facturacion(self):
        """Crear estructura de facturación electrónica"""
        # Crear o obtener Empresa (solo puede haber una)
        empresa = Empresa.objects.first()
        if not empresa:
            empresa = Empresa.objects.create(
                ruc='80012345-1',
                nombre='GroupTours S.A.',
                direccion='Av. Mariscal López 1234, Asunción',
                telefono='+595 21 123-4567',
                correo='info@grouptours.com.py',
                actividades='Agencia de viajes y turismo'
            )
        else:
            # Actualizar datos si ya existe
            empresa.ruc = '80012345-1'
            empresa.nombre = 'GroupTours S.A.'
            empresa.direccion = 'Av. Mariscal López 1234, Asunción'
            empresa.telefono = '+595 21 123-4567'
            empresa.correo = 'info@grouptours.com.py'
            empresa.actividades = 'Agencia de viajes y turismo'
            empresa.save()
        
        # Crear Establecimiento
        establecimiento, _ = Establecimiento.objects.get_or_create(
            empresa=empresa,
            codigo='001',
            defaults={
                'nombre': 'Casa Matriz',
                'direccion': 'Av. Mariscal López 1234, Asunción'
            }
        )
        
        # Crear Punto de Expedición
        punto, _ = PuntoExpedicion.objects.get_or_create(
            establecimiento=establecimiento,
            codigo='001',
            defaults={
                'nombre': 'Punto Principal',
                'descripcion': 'Punto de expedición principal'
            }
        )
        
        # Crear Timbrado
        Timbrado.objects.get_or_create(
            empresa=empresa,
            numero='15234567',
            defaults={
                'inicio_vigencia': date(2025, 1, 1),
                'fin_vigencia': date(2025, 12, 31)
            }
        )
        
        # Crear Tipos de Impuesto
        tipo_iva, _ = TipoImpuesto.objects.get_or_create(
            nombre='IVA',
            defaults={'descripcion': 'Impuesto al Valor Agregado'}
        )
        
        # Crear Subtipos
        SubtipoImpuesto.objects.get_or_create(
            tipo_impuesto=tipo_iva,
            nombre='IVA 10%',
            defaults={'porcentaje': Decimal('10.00')}
        )
        
        SubtipoImpuesto.objects.get_or_create(
            tipo_impuesto=tipo_iva,
            nombre='IVA 5%',
            defaults={'porcentaje': Decimal('5.00')}
        )
        
        self.stdout.write(self.style.SUCCESS('   ✓ Estructura de facturación creada'))

    @transaction.atomic
    def crear_arqueos_caja(self):
        """Crear aperturas de caja para empleados"""
        from apps.facturacion.models import PuntoExpedicion, Establecimiento
        
        empleado_vendedor = Empleado.objects.get(persona__personafisica__documento='3456789')
        empleado_vendedor2 = Empleado.objects.get(persona__personafisica__documento='3678901')
        
        # Obtener o crear puntos de expedición para las cajas
        establecimiento = Establecimiento.objects.first()
        if not establecimiento:
            self.stdout.write(self.style.WARNING('   ⚠️  No hay establecimiento, no se pueden crear cajas'))
            return
        
        # Crear o obtener punto de expedición para caja 1
        punto_exp_1, _ = PuntoExpedicion.objects.get_or_create(
            establecimiento=establecimiento,
            codigo='001',
            defaults={
                'nombre': 'Punto Principal',
                'descripcion': 'Punto de expedición principal'
            }
        )
        
        # Crear o obtener caja 1
        caja1, _ = Caja.objects.get_or_create(
            punto_expedicion=punto_exp_1,
            defaults={
                'nombre': 'Caja Principal',
                'descripcion': 'Caja de ventas principal'
            }
        )
        
        # Crear punto de expedición para caja 2 si no existe
        punto_exp_2, _ = PuntoExpedicion.objects.get_or_create(
            establecimiento=establecimiento,
            codigo='002',
            defaults={
                'nombre': 'Punto Secundario',
                'descripcion': 'Punto de expedición secundario'
            }
        )
        
        # Crear o obtener caja 2
        caja2, _ = Caja.objects.get_or_create(
            punto_expedicion=punto_exp_2,
            defaults={
                'nombre': 'Caja Secundaria',
                'descripcion': 'Caja de ventas secundaria'
            }
        )
        
        # Apertura de caja 1 (simular como cerrada)
        apertura1, created1 = AperturaCaja.objects.get_or_create(
            caja=caja1,
            responsable=empleado_vendedor,
            defaults={
                'monto_inicial': Decimal('1000000'),
                'esta_abierta': False,
                'observaciones_apertura': 'Apertura de prueba cerrada'
            }
        )
        
        # Si se creó, crear también el cierre
        if created1:
            CierreCaja.objects.create(
                apertura_caja=apertura1,
                observaciones_cierre='Cierre de prueba',
                saldo_real_efectivo=Decimal('1500000')
            )
        
        # Apertura de caja 2 (abierta actual)
        apertura2, _ = AperturaCaja.objects.get_or_create(
            caja=caja2,
            responsable=empleado_vendedor2,
            defaults={
                'monto_inicial': Decimal('800000'),
                'esta_abierta': True,
                'observaciones_apertura': 'Apertura actual'
            }
        )
        
        self.stdout.write(self.style.SUCCESS('   ✓ 2 Aperturas de caja creadas (1 cerrada, 1 abierta)'))

    # ========================================================================
    # RESUMEN
    # ========================================================================

    def mostrar_resumen(self):
        """Mostrar resumen de datos creados"""
        resumen = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    RESUMEN DE DATOS CREADOS                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Zonas Geográficas:       {ZonaGeografica.objects.count():>3}                                  ║
║  Nacionalidades:          {Nacionalidad.objects.count():>3}                                  ║
║  Ciudades:                {Ciudad.objects.count():>3}                                  ║
║  Monedas:                 {Moneda.objects.count():>3}                                  ║
║  Cotizaciones:            {CotizacionMoneda.objects.count():>3}                                  ║
║  Tipos de Documento:      {TipoDocumento.objects.count():>3}                                  ║
║  Servicios:               {Servicio.objects.count():>3}                                  ║
║  Hoteles:                 {Hotel.objects.count():>3}                                  ║
║  Habitaciones:            {Habitacion.objects.count():>3}                                  ║
║  Personas Físicas:        {PersonaFisica.objects.count():>3}                                  ║
║  Empleados:               {Empleado.objects.count():>3}                                  ║
║  Usuarios:                {Usuario.objects.count():>3}                                  ║
║  Destinos:                {Destino.objects.count():>3}                                  ║
║  Paquetes:                {Paquete.objects.count():>3}                                  ║
║  Salidas:                 {SalidaPaquete.objects.count():>3}                                  ║
║  Reservas:                {Reserva.objects.count():>3}                                  ║
║  Pasajeros:               {Pasajero.objects.count():>3}                                  ║
║  Aperturas de Caja:       {AperturaCaja.objects.count():>3}                                  ║
╚══════════════════════════════════════════════════════════════════╝

📝 PRÓXIMOS PASOS:
   1. Crear comprobantes de pago (requiere caja abierta)
   2. Generar facturas electrónicas
   3. Actualizar estados de reservas según pagos
   
⚠️  RECORDATORIOS:
   • Usuario: admin / admin123
   • Todos los datos son de prueba
   • Las cotizaciones están actualizadas
"""
        self.stdout.write(resumen)

