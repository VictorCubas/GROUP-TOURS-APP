# apps/paquete/factories.py
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from datetime import date, timedelta
from .models import Paquete, SalidaPaquete, CupoHabitacionSalida, PaqueteServicio, Temporada
from apps.destino.models import Destino
from apps.moneda.models import Moneda
from apps.tipo_paquete.models import TipoPaquete
from apps.hotel.models import Hotel, Habitacion
from apps.servicio.models import Servicio
from apps.distribuidora.models import Distribuidora

fake = Faker('es_ES')


class TemporadaFactory(DjangoModelFactory):
    """Factory para crear Temporadas"""
    
    class Meta:
        model = Temporada
        django_get_or_create = ('nombre',)
    
    nombre = factory.Sequence(lambda n: f'Temporada {n + 1} - {fake.year()}')
    fecha_inicio = factory.LazyFunction(lambda: date.today())
    fecha_fin = factory.LazyAttribute(
        lambda obj: obj.fecha_inicio + timedelta(days=90)
    )


class PaqueteFactory(DjangoModelFactory):
    """Factory para crear Paquetes turísticos"""
    
    class Meta:
        model = Paquete
        skip_postgeneration_save = True
    
    nombre = factory.LazyAttribute(
        lambda obj: f"{fake.city()} {fake.random_element(['Paradise', 'Adventure', 'Relax', 'Tour', 'Experience'])} {fake.random_int(3, 7)} días"
    )
    
    tipo_paquete = factory.LazyFunction(
        lambda: TipoPaquete.objects.filter(activo=True).first() or
                TipoPaquete.objects.create(nombre='Aéreo', descripcion='Paquete con vuelo incluido')
    )
    
    modalidad = factory.Iterator(['flexible', 'fijo'])
    
    destino = factory.LazyFunction(
        lambda: Destino.objects.filter(activo=True).first()
    )
    
    moneda = factory.LazyFunction(
        lambda: Moneda.objects.filter(codigo='USD').first() or
                Moneda.objects.filter(activo=True).first()
    )
    
    propio = True  # Paquetes propios por defecto
    personalizado = False
    cantidad_pasajeros = factory.Faker('random_int', min=20, max=50)
    
    # Distribuidora solo si no es propio (PostGeneration lo maneja)
    distribuidora = None
    
    @factory.post_generation
    def crear_salidas(obj, create, extracted, **kwargs):
        """Crear 1-3 salidas automáticamente para cada paquete"""
        if not create:
            return
        
        # Si el paquete es de distribuidora, no crear salidas con cupos
        if not obj.propio:
            return
        
        # Crear 2 salidas por defecto
        num_salidas = extracted if extracted else 2
        
        for i in range(num_salidas):
            SalidaPaqueteFactory(
                paquete=obj,
                crear_cupos=True  # Crear cupos de habitaciones
            )


class SalidaPaqueteFactory(DjangoModelFactory):
    """Factory para crear Salidas de Paquetes"""
    
    class Meta:
        model = SalidaPaquete
        skip_postgeneration_save = True
    
    paquete = factory.SubFactory(PaqueteFactory)
    
    fecha_salida = factory.LazyFunction(
        lambda: date.today() + timedelta(days=fake.random_int(30, 180))
    )
    
    fecha_regreso = factory.LazyAttribute(
        lambda obj: obj.fecha_salida + timedelta(days=fake.random_int(3, 10))
    )
    
    temporada = factory.LazyFunction(
        lambda: Temporada.objects.first() or TemporadaFactory()
    )
    
    moneda = factory.LazyAttribute(lambda obj: obj.paquete.moneda)
    
    # Precios
    precio_actual = factory.LazyAttribute(
        lambda obj: Decimal(fake.random_int(1000, 5000))
    )
    
    precio_final = factory.LazyAttribute(
        lambda obj: obj.precio_actual * Decimal('2')
    )
    
    ganancia = factory.LazyAttribute(
        lambda obj: Decimal(fake.random_int(10, 25))
    )
    
    cupo = factory.LazyAttribute(lambda obj: obj.paquete.cantidad_pasajeros if obj.paquete else 30)
    senia = factory.LazyAttribute(lambda obj: obj.precio_actual * Decimal('0.2'))
    
    @factory.post_generation
    def hoteles(obj, create, extracted, **kwargs):
        """Asociar 1-2 hoteles a la salida"""
        if not create:
            return
        
        hoteles = extracted if extracted else Hotel.objects.filter(activo=True)[:2]
        if hoteles:
            obj.hoteles.set(hoteles)
    
    @factory.post_generation
    def crear_cupos(obj, create, extracted, **kwargs):
        """Crear cupos de habitaciones para la salida"""
        if not create or not extracted:
            return
        
        # Obtener hoteles de la salida
        hoteles = obj.hoteles.all()
        
        for hotel in hoteles:
            habitaciones = hotel.habitaciones.filter(activo=True)[:3]  # Max 3 tipos de habitación
            
            for habitacion in habitaciones:
                CupoHabitacionSalida.objects.get_or_create(
                    salida=obj,
                    habitacion=habitacion,
                    defaults={'cupo': fake.random_int(3, 10)}
                )


class PaqueteServicioFactory(DjangoModelFactory):
    """Factory para asociar servicios a paquetes"""
    
    class Meta:
        model = PaqueteServicio
    
    paquete = factory.SubFactory(PaqueteFactory)
    servicio = factory.LazyFunction(
        lambda: Servicio.objects.filter(activo=True).first()
    )
    precio = factory.LazyAttribute(
        lambda obj: Decimal(fake.random_int(50, 500))
    )
    incluido = factory.Faker('boolean', chance_of_getting_true=70)

