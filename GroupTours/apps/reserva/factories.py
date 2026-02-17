# apps/reserva/factories.py
import factory
from factory.django import DjangoModelFactory
from faker import Faker
from decimal import Decimal
from .models import Reserva, Pasajero
from apps.persona.models import PersonaFisica
from apps.paquete.models import Paquete, SalidaPaquete
from apps.hotel.models import Habitacion
from apps.tipo_documento.models import TipoDocumento
from apps.nacionalidad.models import Nacionalidad

fake = Faker('es_ES')  # Datos en español


class PersonaFisicaFactory(DjangoModelFactory):
    """Factory para crear PersonaFisica con datos realistas"""
    
    class Meta:
        model = PersonaFisica
        django_get_or_create = ('documento',)  # No crear duplicados por documento
    
    nombre = factory.Faker('first_name', locale='es_ES')
    apellido = factory.Faker('last_name', locale='es_ES')
    documento = factory.Sequence(lambda n: f'{4000000 + n}')
    email = factory.LazyAttribute(
        lambda obj: f'{obj.nombre.lower()}.{obj.apellido.lower()}@example.com'
    )
    telefono = factory.LazyAttribute(
        lambda obj: f'+595 {fake.random_int(900000000, 999999999)}'
    )
    fecha_nacimiento = factory.Faker('date_of_birth', minimum_age=18, maximum_age=80)
    sexo = factory.Iterator(['M', 'F'])
    
    # Relaciones requeridas
    tipo_documento = factory.LazyFunction(
        lambda: TipoDocumento.objects.filter(activo=True).first() or 
                TipoDocumento.objects.create(nombre='CI', codigo='CI', descripcion='Cédula')
    )
    nacionalidad = factory.LazyFunction(
        lambda: Nacionalidad.objects.filter(codigo_alpha2='PY').first() or
                Nacionalidad.objects.create(codigo_alpha2='PY', nombre='Paraguaya', codigo_alpha3='PRY')
    )


class ReservaFactory(DjangoModelFactory):
    """Factory para crear Reservas completas con sus relaciones"""
    
    class Meta:
        model = Reserva
        skip_postgeneration_save = True
    
    titular = factory.SubFactory(PersonaFisicaFactory)
    
    # Seleccionar paquete y salida existentes
    paquete = factory.LazyFunction(
        lambda: Paquete.objects.filter(propio=True, activo=True).first()
    )
    
    salida = factory.LazyAttribute(
        lambda obj: obj.paquete.salidas.filter(activo=True).first() if obj.paquete else None
    )
    
    # Seleccionar una habitación que tenga cupo en la salida
    habitacion = factory.LazyAttribute(
        lambda obj: _obtener_habitacion_con_cupo(obj.salida) if obj.salida else None
    )
    
    cantidad_pasajeros = factory.Faker('random_int', min=1, max=3)
    precio_unitario = factory.LazyAttribute(
        lambda obj: Decimal(fake.random_int(min=1500, max=5000))
    )
    estado = factory.Iterator(['pendiente', 'confirmada'])
    datos_completos = False


def _obtener_habitacion_con_cupo(salida):
    """Obtener una habitación que tenga cupo disponible en la salida"""
    if not salida:
        return None
    
    # Buscar cupos de habitación para esta salida
    from apps.paquete.models import CupoHabitacionSalida
    cupo_disponible = CupoHabitacionSalida.objects.filter(
        salida=salida,
        cupo__gt=0,
        habitacion__activo=True
    ).first()
    
    if cupo_disponible:
        return cupo_disponible.habitacion
    
    # Si no hay cupos, retornar la primera habitación (puede fallar pero es intencional)
    return Habitacion.objects.filter(activo=True).first()


class PasajeroFactory(DjangoModelFactory):
    """Factory para crear Pasajeros"""
    
    class Meta:
        model = Pasajero
    
    reserva = factory.SubFactory(ReservaFactory)
    persona = factory.SubFactory(PersonaFisicaFactory)
    es_titular = False
    por_asignar = False
    precio_asignado = factory.LazyAttribute(
        lambda obj: obj.reserva.precio_unitario if obj.reserva else Decimal('2000')
    )


# Uso en tests o scripts:
# from apps.reserva.factories import ReservaFactory
# 
# # Crear una reserva con todos sus datos relacionados
# reserva = ReservaFactory()
# 
# # Crear 10 reservas
# reservas = ReservaFactory.create_batch(10)
# 
# # Crear con datos específicos
# reserva = ReservaFactory(estado='confirmada', cantidad_pasajeros=3)

