"""
Script para probar la generación de PDF de vouchers.
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.comprobante.models import Voucher


def test_generar_pdf_voucher():
    """
    Prueba la generación de PDF para un voucher existente.
    """
    print("\n" + "="*80)
    print("PRUEBA DE GENERACIÓN DE PDF DE VOUCHER")
    print("="*80 + "\n")

    # Buscar un voucher existente
    voucher = Voucher.objects.filter(activo=True, pasajero__isnull=False).first()

    if not voucher:
        print("[ERROR] No se encontraron vouchers activos con pasajero.")
        return

    print(f"Voucher seleccionado: {voucher.codigo_voucher}")
    print(f"Pasajero: {voucher.pasajero.persona.nombre} {voucher.pasajero.persona.apellido}")
    print(f"Reserva: {voucher.pasajero.reserva.codigo}")
    print(f"Paquete: {voucher.pasajero.reserva.paquete.nombre}")
    print("\n" + "-"*80)

    try:
        print("Generando PDF...")
        pdf = voucher.generar_pdf()
        voucher.save()

        print(f"[OK] PDF generado exitosamente!")
        print(f"Ruta: {voucher.pdf_generado.path}")
        print(f"URL: {voucher.pdf_generado.url}")
        print(f"Tamaño: {voucher.pdf_generado.size} bytes")

        # Verificar que el archivo existe
        if os.path.exists(voucher.pdf_generado.path):
            print("[OK] El archivo PDF existe físicamente")
        else:
            print("[ERROR] El archivo PDF no existe en el sistema de archivos")

    except Exception as e:
        print(f"[ERROR] Error al generar PDF: {e}")
        import traceback
        traceback.print_exc()

    print("-"*80 + "\n")


if __name__ == '__main__':
    test_generar_pdf_voucher()
