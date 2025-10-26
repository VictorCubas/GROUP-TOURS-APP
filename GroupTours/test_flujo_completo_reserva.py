#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba: FLUJO COMPLETO DE RESERVA CON COMPROBANTES
Simula el ciclo de vida completo de una reserva desde la creación hasta los pagos.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva, Pasajero
from apps.comprobante.models import ComprobantePago, ComprobantePagoDistribucion, Voucher
from apps.persona.models import PersonaFisica
from apps.paquete.models import Paquete, SalidaPaquete
from apps.hotel.models import Habitacion
from apps.empleado.models import Empleado
from decimal import Decimal
import json


def print_separator():
    print("\n" + "=" * 80 + "\n")


def print_section(title):
    print_separator()
    print(f">>> {title}")
    print_separator()


def mostrar_estado_cuenta(pasajero):
    """Muestra el estado de cuenta de un pasajero"""
    print(f"\n--- Estado de Cuenta: {pasajero.persona.nombre} {pasajero.persona.apellido} ---")
    print(f"    ID Pasajero: {pasajero.id}")
    print(f"    Es titular: {'SI' if pasajero.es_titular else 'NO'}")
    print(f"    Precio asignado: ${pasajero.precio_asignado or 0}")
    print(f"    Monto pagado: ${pasajero.monto_pagado}")
    print(f"    Saldo pendiente: ${pasajero.saldo_pendiente}")
    print(f"    Porcentaje pagado: {pasajero.porcentaje_pagado}%")
    print(f"    Sena requerida: ${pasajero.seña_requerida}")
    print(f"    Sena pagada: {'[SI]' if pasajero.tiene_sena_pagada else '[NO]'}")
    print(f"    Totalmente pagado: {'[SI]' if pasajero.esta_totalmente_pagado else '[NO]'}")

    # Mostrar historial
    distribuciones = pasajero.distribuciones_pago.all()
    if distribuciones.count() > 0:
        print(f"\n    Historial de pagos ({distribuciones.count()}):")
        for i, dist in enumerate(distribuciones, 1):
            print(f"      {i}. {dist.comprobante.numero_comprobante} - "
                  f"{dist.comprobante.get_tipo_display()} - ${dist.monto} "
                  f"({dist.comprobante.fecha_pago.strftime('%Y-%m-%d')})")
    else:
        print("    (Sin pagos registrados)")


def paso_1_crear_reserva():
    """PASO 1: Crear una reserva nueva"""
    print_section("PASO 1: CREAR RESERVA")

    # Buscar datos necesarios
    print("Buscando datos necesarios...")

    # Buscar una salida que tenga cupos de habitaciones configurados (para paquetes propios)
    from apps.paquete.models import CupoHabitacionSalida

    salida = SalidaPaquete.objects.filter(
        cupos_habitaciones__isnull=False,
        activo=True
    ).distinct().first()

    if not salida:
        print("[ERROR] No hay salidas con cupos configurados en la BD")
        return None

    paquete = salida.paquete
    print(f"[OK] Paquete seleccionado: {paquete.nombre}")
    print(f"[OK] Salida seleccionada: {salida.fecha_salida} - {salida.fecha_regreso or 'Sin fecha regreso'}")

    # Buscar una habitación que tenga cupo disponible en esta salida
    cupo_habitacion = salida.cupos_habitaciones.filter(cupo__gt=0).first()
    if not cupo_habitacion:
        print("[ERROR] No hay cupos disponibles en esta salida")
        return None

    habitacion = cupo_habitacion.habitacion
    print(f"[OK] Habitacion seleccionada: {habitacion.numero} ({habitacion.get_tipo_display()}) - Hotel: {habitacion.hotel.nombre}")
    print(f"    Cupos disponibles: {cupo_habitacion.cupo}")

    # Buscar 2 personas para ser pasajeros
    personas = PersonaFisica.objects.all()[:2]
    if personas.count() < 2:
        print("[ERROR] Se necesitan al menos 2 personas en la BD")
        return None

    titular = personas[0]
    pasajero_2 = personas[1]
    print(f"[OK] Titular: {titular.nombre} {titular.apellido}")
    print(f"[OK] Pasajero 2: {pasajero_2.nombre} {pasajero_2.apellido}")

    # Crear la reserva
    print("\nCreando reserva...")
    reserva = Reserva.objects.create(
        titular=titular,
        paquete=paquete,
        salida=salida,
        habitacion=habitacion,
        cantidad_pasajeros=2,
        observacion="Reserva de prueba - Flujo completo"
    )

    # Calcular y asignar precio unitario
    reserva.precio_unitario = reserva.calcular_precio_unitario()
    reserva.save(update_fields=['precio_unitario'])

    print(f"[OK] Reserva creada: {reserva.codigo}")
    print(f"    Paquete: {reserva.paquete.nombre}")
    print(f"    Salida: {reserva.salida.fecha_salida}")
    print(f"    Habitacion: {reserva.habitacion.numero}")
    print(f"    Cantidad pasajeros: {reserva.cantidad_pasajeros}")
    print(f"    Precio unitario: ${reserva.precio_unitario}")
    print(f"    Costo total estimado: ${reserva.costo_total_estimado}")
    print(f"    Sena total requerida: ${reserva.seña_total}")
    print(f"    Estado: {reserva.estado}")

    # Crear pasajeros
    print("\nCreando pasajeros...")
    pasajero1 = Pasajero.objects.create(
        reserva=reserva,
        persona=titular,
        es_titular=True,
        precio_asignado=reserva.precio_unitario
    )
    print(f"[OK] Pasajero 1 (Titular): {pasajero1.persona.nombre} - Precio: ${pasajero1.precio_asignado}")

    pasajero2 = Pasajero.objects.create(
        reserva=reserva,
        persona=pasajero_2,
        es_titular=False,
        precio_asignado=reserva.precio_unitario
    )
    print(f"[OK] Pasajero 2: {pasajero2.persona.nombre} - Precio: ${pasajero2.precio_asignado}")

    # Actualizar estado de la reserva
    reserva.actualizar_estado()
    print(f"\nEstado actualizado: {reserva.estado_display}")

    return reserva


def paso_2_registrar_sena(reserva):
    """PASO 2: Registrar pago de seña"""
    print_section("PASO 2: REGISTRAR PAGO DE SENA")

    if not reserva:
        print("[ERROR] No hay reserva")
        return None

    print(f"Reserva: {reserva.codigo}")
    print(f"Sena total requerida: ${reserva.seña_total}")

    # Obtener empleado
    empleado = Empleado.objects.first()
    if not empleado:
        print("[ERROR] No hay empleados en la BD")
        return None

    # Calcular seña por pasajero (50% del precio)
    pasajeros = reserva.pasajeros.all()
    sena_por_pasajero = reserva.salida.senia if reserva.salida.senia else reserva.precio_unitario * Decimal('0.30')
    monto_total_sena = sena_por_pasajero * reserva.cantidad_pasajeros

    print(f"\nCreando comprobante de sena...")
    print(f"  Sena por pasajero: ${sena_por_pasajero}")
    print(f"  Cantidad pasajeros: {reserva.cantidad_pasajeros}")
    print(f"  Monto total: ${monto_total_sena}")

    # Crear comprobante
    comprobante = ComprobantePago.objects.create(
        reserva=reserva,
        tipo='sena',
        monto=monto_total_sena,
        metodo_pago='transferencia',
        empleado=empleado,
        referencia='TRANS-001-TEST',
        observaciones='Pago de sena - Transferencia bancaria'
    )
    print(f"[OK] Comprobante creado: {comprobante.numero_comprobante}")

    # Crear distribuciones para cada pasajero
    print(f"\nDistribuyendo pago entre {pasajeros.count()} pasajeros:")
    for pasajero in pasajeros:
        distribucion = ComprobantePagoDistribucion.objects.create(
            comprobante=comprobante,
            pasajero=pasajero,
            monto=sena_por_pasajero,
            observaciones=f"Sena - {'Titular' if pasajero.es_titular else 'Acompanante'}"
        )
        print(f"  [OK] {pasajero.persona.nombre}: ${distribucion.monto}")

    # Validar distribuciones
    comprobante.validar_distribuciones()
    print(f"\n[OK] Distribuciones validadas correctamente")

    # Actualizar monto en reserva
    comprobante.actualizar_monto_reserva()
    reserva.refresh_from_db()

    print(f"\n[OK] Monto pagado actualizado en reserva: ${reserva.monto_pagado}")
    print(f"Estado de la reserva: {reserva.estado_display}")

    return comprobante


def paso_3_verificar_voucher(reserva):
    """PASO 3: Verificar que se creó el voucher automáticamente"""
    print_section("PASO 3: VERIFICAR VOUCHER")

    if not reserva:
        print("[ERROR] No hay reserva")
        return None

    print(f"Verificando voucher para reserva: {reserva.codigo}")
    print(f"Estado de la reserva: {reserva.estado}")

    try:
        voucher = reserva.voucher
        print(f"\n[OK] Voucher encontrado!")
        print(f"    Codigo: {voucher.codigo_voucher}")
        print(f"    Fecha emision: {voucher.fecha_emision}")
        print(f"    Activo: {'SI' if voucher.activo else 'NO'}")
        print(f"    QR generado: {'SI' if voucher.qr_code else 'NO'}")
        print(f"    PDF generado: {'SI' if voucher.pdf_generado else 'NO'}")
        return voucher
    except Voucher.DoesNotExist:
        print(f"\n[WARN] No se encontro voucher para esta reserva")
        print(f"      Esto es normal si la reserva no esta confirmada.")
        print(f"      Estado actual: {reserva.estado}")
        return None


def paso_4_consultar_estados_cuenta(reserva):
    """PASO 4: Consultar estado de cuenta de cada pasajero"""
    print_section("PASO 4: ESTADO DE CUENTA DE PASAJEROS")

    if not reserva:
        print("[ERROR] No hay reserva")
        return

    pasajeros = reserva.pasajeros.all()
    print(f"Reserva: {reserva.codigo}")
    print(f"Total pasajeros: {pasajeros.count()}")
    print(f"Costo total: ${reserva.costo_total_estimado}")
    print(f"Monto pagado: ${reserva.monto_pagado}")
    print(f"Saldo pendiente: ${reserva.costo_total_estimado - reserva.monto_pagado}")

    for pasajero in pasajeros:
        mostrar_estado_cuenta(pasajero)


def paso_5_pago_parcial(reserva):
    """PASO 5: Registrar un pago parcial adicional"""
    print_section("PASO 5: REGISTRAR PAGO PARCIAL")

    if not reserva:
        print("[ERROR] No hay reserva")
        return None

    print(f"Reserva: {reserva.codigo}")

    # Obtener empleado
    empleado = Empleado.objects.first()

    # Pagar más a uno de los pasajeros (por ejemplo, $1000 al pasajero 1)
    pasajero1 = reserva.pasajeros.filter(es_titular=True).first()
    monto_pago = Decimal('1000.00')

    print(f"\nRegistrando pago parcial de ${monto_pago} para {pasajero1.persona.nombre}")

    comprobante = ComprobantePago.objects.create(
        reserva=reserva,
        tipo='pago_parcial',
        monto=monto_pago,
        metodo_pago='efectivo',
        empleado=empleado,
        referencia='EFVO-002-TEST',
        observaciones='Pago parcial en efectivo'
    )
    print(f"[OK] Comprobante creado: {comprobante.numero_comprobante}")

    # Distribuir todo el monto a un solo pasajero
    distribucion = ComprobantePagoDistribucion.objects.create(
        comprobante=comprobante,
        pasajero=pasajero1,
        monto=monto_pago,
        observaciones='Pago parcial del titular'
    )
    print(f"[OK] Distribucion creada: ${distribucion.monto} para {pasajero1.persona.nombre}")

    # Actualizar reserva
    comprobante.actualizar_monto_reserva()
    reserva.refresh_from_db()

    print(f"\n[OK] Monto pagado actualizado: ${reserva.monto_pagado}")
    print(f"Estado: {reserva.estado_display}")

    return comprobante


def paso_6_verificar_actualizaciones(reserva):
    """PASO 6: Verificar que todo se actualizó correctamente"""
    print_section("PASO 6: VERIFICACION FINAL")

    if not reserva:
        print("[ERROR] No hay reserva")
        return

    reserva.refresh_from_db()

    print(f"RESUMEN FINAL DE LA RESERVA: {reserva.codigo}")
    print(f"\nDatos generales:")
    print(f"  Paquete: {reserva.paquete.nombre}")
    print(f"  Fecha salida: {reserva.salida.fecha_salida}")
    print(f"  Cantidad pasajeros: {reserva.cantidad_pasajeros}")
    print(f"  Estado: {reserva.estado_display}")

    print(f"\nFinanzas:")
    print(f"  Costo total estimado: ${reserva.costo_total_estimado}")
    print(f"  Monto pagado: ${reserva.monto_pagado}")
    print(f"  Saldo pendiente: ${reserva.costo_total_estimado - reserva.monto_pagado}")
    print(f"  Porcentaje pagado: {(reserva.monto_pagado / reserva.costo_total_estimado * 100):.2f}%")

    print(f"\nPasajeros:")
    for pasajero in reserva.pasajeros.all():
        print(f"  - {pasajero.persona.nombre}: "
              f"Pagado ${pasajero.monto_pagado} de ${pasajero.precio_asignado} "
              f"({pasajero.porcentaje_pagado}%)")

    print(f"\nComprobantes emitidos:")
    comprobantes = reserva.comprobantes.filter(activo=True)
    total_comprobantes = Decimal('0')
    for comp in comprobantes:
        print(f"  - {comp.numero_comprobante}: {comp.get_tipo_display()} - "
              f"${comp.monto} ({comp.get_metodo_pago_display()})")
        total_comprobantes += comp.monto
    print(f"  Total en comprobantes: ${total_comprobantes}")

    # Verificar voucher
    try:
        voucher = reserva.voucher
        print(f"\nVoucher: {voucher.codigo_voucher}")
        print(f"  Emitido: {voucher.fecha_emision.strftime('%Y-%m-%d %H:%M')}")
    except Voucher.DoesNotExist:
        print(f"\nVoucher: No generado (reserva debe estar confirmada)")


def main():
    """Ejecutar flujo completo"""
    print_section("PRUEBA DE FLUJO COMPLETO: RESERVA CON COMPROBANTES")
    print("Este script simula el ciclo completo de una reserva:")
    print("  1. Crear reserva con pasajeros")
    print("  2. Registrar pago de sena")
    print("  3. Verificar voucher automatico")
    print("  4. Consultar estados de cuenta")
    print("  5. Registrar pago parcial adicional")
    print("  6. Verificacion final")

    input("\nPresiona ENTER para continuar...")

    # PASO 1: Crear reserva
    reserva = paso_1_crear_reserva()
    if not reserva:
        print("\n[ERROR] No se pudo crear la reserva. Abortando.")
        return

    input("\nPresiona ENTER para continuar con el pago de sena...")

    # PASO 2: Pagar seña
    comprobante_sena = paso_2_registrar_sena(reserva)
    if not comprobante_sena:
        print("\n[ERROR] No se pudo registrar la sena. Abortando.")
        return

    input("\nPresiona ENTER para verificar el voucher...")

    # PASO 3: Verificar voucher
    voucher = paso_3_verificar_voucher(reserva)

    input("\nPresiona ENTER para consultar estados de cuenta...")

    # PASO 4: Estados de cuenta
    paso_4_consultar_estados_cuenta(reserva)

    input("\nPresiona ENTER para registrar un pago parcial adicional...")

    # PASO 5: Pago parcial
    comprobante_parcial = paso_5_pago_parcial(reserva)

    input("\nPresiona ENTER para ver la verificacion final...")

    # PASO 6: Verificación final
    paso_6_verificar_actualizaciones(reserva)

    # Estados de cuenta actualizados
    paso_4_consultar_estados_cuenta(reserva)

    print_section("PRUEBA COMPLETADA")
    print(f"Reserva creada: {reserva.codigo}")
    print(f"ID Reserva: {reserva.id}")
    print(f"\nPuedes consultar en la API:")
    print(f"  GET /api/reservas/{reserva.id}/")
    print(f"  GET /api/reservas/{reserva.id}/comprobantes/")
    print(f"  GET /api/reservas/pasajeros/?reserva_id={reserva.id}")

    for pasajero in reserva.pasajeros.all():
        print(f"  GET /api/reservas/pasajeros/{pasajero.id}/estado-cuenta/")

    print("\n")


if __name__ == '__main__':
    main()
