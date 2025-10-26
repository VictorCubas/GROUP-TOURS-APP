#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de prueba: Generar PDF de comprobante
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.comprobante.models import ComprobantePago


def main():
    print("\n" + "=" * 80)
    print("PRUEBA DE GENERACION DE PDF DE COMPROBANTE")
    print("=" * 80 + "\n")

    # Obtener el último comprobante
    comprobante = ComprobantePago.objects.filter(activo=True).order_by('-fecha_pago').first()

    if not comprobante:
        print("[ERROR] No hay comprobantes en la base de datos")
        return

    print(f"Comprobante seleccionado: {comprobante.numero_comprobante}")
    print(f"  Reserva: {comprobante.reserva.codigo}")
    print(f"  Tipo: {comprobante.get_tipo_display()}")
    print(f"  Monto: ${comprobante.monto}")
    print(f"  Fecha: {comprobante.fecha_pago}")
    print(f"  Distribuciones: {comprobante.distribuciones.count()}")

    print("\nGenerando PDF...")

    try:
        pdf_file = comprobante.generar_pdf()
        comprobante.save()

        print(f"\n[OK] PDF generado exitosamente!")
        print(f"  Ruta: {comprobante.pdf_generado.path}")
        print(f"  URL: {comprobante.pdf_generado.url}")
        print(f"  Tamano: {comprobante.pdf_generado.size / 1024:.2f} KB")

        print("\n" + "=" * 80)
        print("COMO DESCARGAR EL PDF:")
        print("=" * 80)
        print(f"\n1. Via API:")
        print(f"   GET http://localhost:8000/api/comprobantes/{comprobante.id}/descargar-pdf/")
        print(f"\n2. Via navegador:")
        print(f"   http://localhost:8000/api/comprobantes/{comprobante.id}/descargar-pdf/")
        print(f"\n3. Regenerar forzosamente:")
        print(f"   http://localhost:8000/api/comprobantes/{comprobante.id}/descargar-pdf/?regenerar=true")
        print(f"\n4. Ver archivo directamente:")
        print(f"   {comprobante.pdf_generado.path}")

        print("\n" + "=" * 80)
        print("[OK] Prueba completada exitosamente!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Error al generar PDF: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
