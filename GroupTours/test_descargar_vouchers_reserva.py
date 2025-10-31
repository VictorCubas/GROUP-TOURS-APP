"""
Script de ejemplo para demostrar la descarga de vouchers de una reserva.
Este script muestra cómo usar la API para:
1. Obtener detalles de una reserva
2. Identificar pasajeros con voucher disponible
3. Descargar los PDFs de los vouchers
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.reserva.models import Reserva
from apps.reserva.serializers import ReservaDetalleSerializer


def descargar_vouchers_de_reserva(reserva_id):
    """
    Simula el flujo de descarga de vouchers desde la API.
    """
    print("\n" + "="*80)
    print(f"DESCARGA DE VOUCHERS - RESERVA {reserva_id}")
    print("="*80 + "\n")

    # PASO 1: Obtener detalles de la reserva (simula GET /api/reservas/{id}/)
    try:
        reserva = Reserva.objects.get(id=reserva_id)
    except Reserva.DoesNotExist:
        print(f"[ERROR] No se encontró la reserva con ID {reserva_id}")
        return

    # Serializar (esto es lo que retorna la API)
    serializer = ReservaDetalleSerializer(reserva)
    data = serializer.data

    print(f"[OK] Reserva obtenida: {data['codigo']}")
    print(f"[OK] Estado: {data['estado_display']}")
    print(f"[OK] Cantidad de pasajeros: {data['cantidad_pasajeros']}")
    print(f"[OK] Costo total: ${data['costo_total_estimado']}")
    print(f"[OK] Monto pagado: ${data['monto_pagado']}")
    print(f"[OK] Saldo pendiente: ${data['saldo_pendiente']}")

    # PASO 2: Analizar pasajeros
    print("\n" + "-"*80)
    print("PASAJEROS DE LA RESERVA:")
    print("-"*80 + "\n")

    vouchers_disponibles = []
    pasajeros_sin_voucher = []

    for pasajero in data['pasajeros']:
        nombre = f"{pasajero['persona']['nombre']} {pasajero['persona']['apellido']}"
        voucher_id = pasajero.get('voucher_id')
        voucher_codigo = pasajero.get('voucher_codigo')

        print(f"Pasajero: {nombre}")
        print(f"  - ID: {pasajero['id']}")
        print(f"  - Es Titular: {'SI' if pasajero['es_titular'] else 'NO'}")
        print(f"  - Por Asignar: {'SI' if pasajero['por_asignar'] else 'NO'}")
        print(f"  - Precio Asignado: ${pasajero['precio_asignado']}")
        print(f"  - Monto Pagado: ${pasajero['monto_pagado']}")
        print(f"  - Saldo Pendiente: ${pasajero['saldo_pendiente']}")
        print(f"  - Totalmente Pagado: {'SI' if pasajero['esta_totalmente_pagado'] else 'NO'}")

        if voucher_id:
            print(f"  - Voucher ID: {voucher_id}")
            print(f"  - Voucher Código: {voucher_codigo}")
            print(f"  - Estado: [OK] VOUCHER DISPONIBLE")
            vouchers_disponibles.append({
                'pasajero_nombre': nombre,
                'voucher_id': voucher_id,
                'voucher_codigo': voucher_codigo,
            })
        else:
            if not pasajero['esta_totalmente_pagado']:
                razon = f"Saldo pendiente: ${pasajero['saldo_pendiente']}"
            elif pasajero['por_asignar']:
                razon = "Datos del pasajero pendientes (por_asignar=True)"
            else:
                razon = "Condiciones no cumplidas"

            print(f"  - Estado: [WARN] SIN VOUCHER - {razon}")
            pasajeros_sin_voucher.append({
                'pasajero_nombre': nombre,
                'razon': razon
            })

        print()

    # PASO 3: Resumen y descarga de vouchers
    print("-"*80)
    print("RESUMEN:")
    print("-"*80 + "\n")

    print(f"Total de pasajeros: {len(data['pasajeros'])}")
    print(f"Vouchers disponibles: {len(vouchers_disponibles)}")
    print(f"Pasajeros sin voucher: {len(pasajeros_sin_voucher)}")

    if vouchers_disponibles:
        print("\n" + "="*80)
        print("DESCARGANDO VOUCHERS...")
        print("="*80 + "\n")

        # Crear directorio para guardar PDFs
        output_dir = os.path.join(os.getcwd(), 'vouchers_descargados')
        os.makedirs(output_dir, exist_ok=True)

        for voucher_info in vouchers_disponibles:
            print(f"[INFO] Procesando voucher para: {voucher_info['pasajero_nombre']}")
            print(f"       Voucher ID: {voucher_info['voucher_id']}")
            print(f"       Código: {voucher_info['voucher_codigo']}")

            # Simular descarga (GET /api/vouchers/{id}/descargar-pdf/)
            from apps.comprobante.models import Voucher

            try:
                voucher = Voucher.objects.get(id=voucher_info['voucher_id'])

                # Generar PDF si no existe
                if not voucher.pdf_generado:
                    print(f"       [INFO] Generando PDF...")
                    voucher.generar_pdf()
                    voucher.save()
                else:
                    print(f"       [INFO] PDF ya existe, reutilizando...")

                # Información del archivo
                pdf_path = voucher.pdf_generado.path
                pdf_size = voucher.pdf_generado.size

                print(f"       [OK] PDF disponible")
                print(f"       Ruta: {pdf_path}")
                print(f"       Tamaño: {pdf_size:,} bytes ({pdf_size/1024:.2f} KB)")

                # En una aplicación real, aquí se retornaría el archivo como respuesta HTTP
                # response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
                # response['Content-Disposition'] = f'attachment; filename="{filename}"'

                print(f"       [OK] Descarga simulada exitosa!")

            except Voucher.DoesNotExist:
                print(f"       [ERROR] Voucher no encontrado en la base de datos")
            except Exception as e:
                print(f"       [ERROR] Error al procesar voucher: {e}")

            print()

        print("="*80)
        print(f"[RESUMEN] {len(vouchers_disponibles)} voucher(s) procesado(s)")
        print("="*80)

    else:
        print("\n[INFO] No hay vouchers disponibles para descargar")
        if pasajeros_sin_voucher:
            print("\n[INFO] Razones:")
            for info in pasajeros_sin_voucher:
                print(f"  - {info['pasajero_nombre']}: {info['razon']}")

    print("\n" + "="*80)
    print("ENDPOINTS API CORRESPONDIENTES:")
    print("="*80)
    print(f"\n1. Obtener detalles de reserva:")
    print(f"   GET /api/reservas/{reserva_id}/")
    print(f"   URL: http://localhost:8000/api/reservas/{reserva_id}/")

    if vouchers_disponibles:
        print(f"\n2. Descargar vouchers:")
        for voucher_info in vouchers_disponibles:
            print(f"   GET /api/vouchers/{voucher_info['voucher_id']}/descargar-pdf/")
            print(f"   URL: http://localhost:8000/api/vouchers/{voucher_info['voucher_id']}/descargar-pdf/")

    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    # Probar con la reserva 179
    descargar_vouchers_de_reserva(179)
