#!/usr/bin/env python
"""
Script de prueba para el endpoint de estado de cuenta de pasajeros.
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion
from apps.reserva.models import Pasajero
from apps.empleado.models import Empleado
from apps.reserva.serializers import PasajeroEstadoCuentaSerializer
from decimal import Decimal
import json


def crear_comprobante_ejemplo():
    """Crea un comprobante de ejemplo si no existen"""
    print(f'Comprobantes existentes: {ComprobantePago.objects.count()}')
    print(f'Distribuciones existentes: {ComprobantePagoDistribucion.objects.count()}')

    if ComprobantePago.objects.count() == 0:
        print('\n[Creando comprobante de ejemplo...]')

        # Obtener datos necesarios
        pasajero = Pasajero.objects.first()
        if not pasajero:
            print('ERROR: No hay pasajeros en la BD')
            return None

        reserva = pasajero.reserva

        # Obtener empleado
        empleado = Empleado.objects.first()
        if not empleado:
            print('ERROR: No hay empleados en la BD')
            return None

        # Actualizar precio_asignado del pasajero si es None
        if pasajero.precio_asignado is None:
            pasajero.precio_asignado = Decimal('5000.00')
            pasajero.save()
            print(f'[OK] Precio asignado actualizado: {pasajero.precio_asignado}')

        # Crear comprobante de seña
        comprobante = ComprobantePago.objects.create(
            reserva=reserva,
            tipo='sena',
            monto=Decimal('1500.00'),
            metodo_pago='transferencia',
            empleado=empleado,
            referencia='REF-TEST-001',
            observaciones='Comprobante de prueba para demostracion'
        )
        print(f'[OK] Comprobante creado: {comprobante.numero_comprobante}')

        # Crear distribución para el pasajero
        distribucion = ComprobantePagoDistribucion.objects.create(
            comprobante=comprobante,
            pasajero=pasajero,
            monto=Decimal('1500.00'),
            observaciones='Sena del pasajero titular'
        )
        print(f'[OK] Distribucion creada: ${distribucion.monto} para {pasajero.persona.nombre}')

        # Actualizar monto en reserva
        comprobante.actualizar_monto_reserva()
        print(f'[OK] Monto de reserva actualizado: ${reserva.monto_pagado}')

        return pasajero
    else:
        print('Ya existen comprobantes en la BD\n')
        # Obtener un pasajero que tenga pagos
        distribucion = ComprobantePagoDistribucion.objects.first()
        if distribucion:
            return distribucion.pasajero
        return Pasajero.objects.first()


def test_estado_cuenta(pasajero_id=None):
    """Prueba el serializer de estado de cuenta"""
    if pasajero_id:
        pasajero = Pasajero.objects.filter(id=pasajero_id).first()
    else:
        pasajero = Pasajero.objects.first()

    if not pasajero:
        print('No hay pasajeros en la base de datos')
        return

    print(f'\n{"=" * 80}')
    print(f'ESTADO DE CUENTA - PASAJERO ID: {pasajero.id}')
    print(f'{"=" * 80}\n')

    serializer = PasajeroEstadoCuentaSerializer(pasajero)
    data = serializer.data

    # Mostrar información de manera legible
    print(f'INFORMACION BASICA')
    print(f'   Nombre: {data["persona"]["nombre"]} {data["persona"]["apellido"]}')
    print(f'   Documento: {data["persona"]["documento"]}')
    print(f'   Email: {data["persona"]["email"]}')
    print(f'   Telefono: {data["persona"]["telefono"]}')
    print(f'   Es titular: {"Si" if data["es_titular"] else "No"}')
    print(f'   Reserva: {data["reserva_codigo"]}')
    print(f'   Paquete: {data["paquete_nombre"]}')

    print(f'\nESTADO FINANCIERO')
    print(f'   Precio asignado: ${data["precio_asignado"] or "0.00"}')
    print(f'   Monto pagado: ${data["monto_pagado"]}')
    print(f'   Saldo pendiente: ${data["saldo_pendiente"]}')
    print(f'   Porcentaje pagado: {data["porcentaje_pagado"]}%')
    print(f'   Sena requerida: ${data["seña_requerida"]}')
    print(f'   Sena pagada: {"[SI]" if data["tiene_sena_pagada"] else "[NO]"}')
    print(f'   Totalmente pagado: {"[SI]" if data["esta_totalmente_pagado"] else "[NO]"}')

    print(f'\nHISTORIAL DE PAGOS ({len(data["historial_pagos"])} pagos)')
    if data["historial_pagos"]:
        for i, pago in enumerate(data["historial_pagos"], 1):
            print(f'\n   Pago #{i}:')
            print(f'      Fecha: {pago["fecha_pago"]}')
            print(f'      Comprobante: {pago["numero_comprobante"]}')
            print(f'      Tipo: {pago["tipo_display"]}')
            print(f'      Metodo: {pago["metodo_pago_display"]}')
            print(f'      Monto: ${pago["monto_distribuido"]}')
            print(f'      Activo: {"[SI]" if pago["comprobante_activo"] else "[NO]"}')
            if pago["observaciones"]:
                print(f'      Observaciones: {pago["observaciones"]}')
    else:
        print('   (Sin pagos registrados)')

    print(f'\n{"=" * 80}')
    print(f'JSON COMPLETO:')
    print(f'{"=" * 80}')
    print(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    print(f'{"=" * 80}\n')


if __name__ == '__main__':
    print('\n[PRUEBA DEL ENDPOINT DE ESTADO DE CUENTA]\n')

    # Crear comprobante de ejemplo si no existe
    pasajero = crear_comprobante_ejemplo()

    # Probar el serializer
    if pasajero:
        test_estado_cuenta(pasajero.id)
    else:
        test_estado_cuenta()

    print('\n[Prueba completada]\n')
    print('Para probar el endpoint via API:')
    print(f'   GET http://localhost:8000/api/reservas/pasajeros/1/estado-cuenta/')
