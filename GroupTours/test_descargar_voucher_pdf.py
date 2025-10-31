"""
Script para probar la descarga de PDF del voucher de un pasajero no titular.
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.comprobante.models import Voucher


def test_descargar_voucher_pdf():
    """
    Prueba la generación y descarga de PDF para el voucher ID 136
    (Pasajero no titular: Maria Andrea Escurra Caceres)
    """
    print("\n" + "="*80)
    print("PRUEBA DE DESCARGA DE PDF - PASAJERO NO TITULAR")
    print("="*80 + "\n")

    # Obtener el voucher ID 136
    try:
        voucher = Voucher.objects.get(id=136)
    except Voucher.DoesNotExist:
        print("[ERROR] No se encontro el voucher con ID 136")
        return

    print("INFORMACION DEL VOUCHER:")
    print("-"*80)
    print(f"ID Voucher: {voucher.id}")
    print(f"Codigo: {voucher.codigo_voucher}")
    print(f"Pasajero: {voucher.pasajero.persona.nombre} {voucher.pasajero.persona.apellido}")
    print(f"Es Titular: {'SI' if voucher.pasajero.es_titular else 'NO'}")
    print(f"Por Asignar: {'SI' if voucher.pasajero.por_asignar else 'NO'}")
    print(f"Reserva: {voucher.pasajero.reserva.codigo}")
    print(f"Paquete: {voucher.pasajero.reserva.paquete.nombre}")
    print(f"Precio Asignado: ${voucher.pasajero.precio_asignado}")
    print(f"Monto Pagado: ${voucher.pasajero.monto_pagado}")
    print(f"Saldo Pendiente: ${voucher.pasajero.saldo_pendiente}")
    print(f"Esta Totalmente Pagado: {'SI' if voucher.pasajero.esta_totalmente_pagado else 'NO'}")

    # Información de la salida
    if voucher.pasajero.reserva.salida:
        salida = voucher.pasajero.reserva.salida
        print(f"\nINFORMACION DE LA SALIDA:")
        print(f"Fecha Salida: {salida.fecha_salida}")
        print(f"Fecha Regreso: {salida.fecha_regreso}")
        if salida.fecha_salida and salida.fecha_regreso:
            duracion = (salida.fecha_regreso - salida.fecha_salida).days
            print(f"Duracion: {duracion} dias")

    # Información del hotel
    if voucher.pasajero.reserva.habitacion:
        habitacion = voucher.pasajero.reserva.habitacion
        hotel = habitacion.hotel
        print(f"\nINFORMACION DEL HOTEL:")
        print(f"Hotel: {hotel.nombre}")
        if hasattr(hotel, 'ciudad') and hotel.ciudad:
            print(f"Ciudad: {hotel.ciudad.nombre}")
        if hasattr(hotel, 'estrellas') and hotel.estrellas:
            print(f"Categoria: {hotel.estrellas} estrellas")
        print(f"Habitacion: {habitacion.get_tipo_display()} - N° {habitacion.numero}")
        print(f"Capacidad: {habitacion.capacidad} persona(s)")

    print("\n" + "="*80)
    print("GENERANDO PDF...")
    print("="*80 + "\n")

    try:
        # Generar el PDF
        pdf = voucher.generar_pdf()
        voucher.save()

        print("[OK] PDF generado exitosamente!")
        print(f"\nRuta completa: {voucher.pdf_generado.path}")
        print(f"URL relativa: {voucher.pdf_generado.url}")
        print(f"Tamanio: {voucher.pdf_generado.size:,} bytes ({voucher.pdf_generado.size/1024:.2f} KB)")

        # Verificar que el archivo existe
        if os.path.exists(voucher.pdf_generado.path):
            print("\n[OK] El archivo PDF existe fisicamente en el sistema")

            # Información del archivo
            file_stats = os.stat(voucher.pdf_generado.path)
            print(f"\nDETALLES DEL ARCHIVO:")
            print(f"- Nombre: {os.path.basename(voucher.pdf_generado.path)}")
            print(f"- Directorio: {os.path.dirname(voucher.pdf_generado.path)}")
            print(f"- Tamanio: {file_stats.st_size:,} bytes")

            # Verificar que tiene el QR code
            if voucher.qr_code:
                print(f"\n[OK] El voucher tiene codigo QR: {voucher.qr_code.url}")
            else:
                print(f"\n[WARN] El voucher NO tiene codigo QR generado")

        else:
            print("\n[ERROR] El archivo PDF no existe en el sistema de archivos")

        print("\n" + "="*80)
        print("ENDPOINT API PARA DESCARGA:")
        print("="*80)
        print(f"\nGET /api/vouchers/{voucher.id}/descargar-pdf/")
        print(f"\nURL completa (desarrollo):")
        print(f"http://localhost:8000/api/vouchers/{voucher.id}/descargar-pdf/")
        print(f"\nCon regeneracion forzada:")
        print(f"http://localhost:8000/api/vouchers/{voucher.id}/descargar-pdf/?regenerar=true")

    except Exception as e:
        print(f"[ERROR] Error al generar PDF: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    test_descargar_voucher_pdf()
