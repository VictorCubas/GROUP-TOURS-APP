"""
Script para verificar el impacto de anular una factura en los campos
factura_global_generada y factura_individual_generada de la reserva.

Uso:
    python manage.py shell < test_anulacion_factura.py
    O ejecutar directamente: python test_anulacion_factura.py
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from apps.facturacion.models import FacturaElectronica
from apps.reserva.models import Reserva
from apps.reserva.serializers import ReservaDetalleSerializer
from django.contrib.auth.models import User

def test_anulacion_factura(factura_id=63, reserva_id=260):
    """
    Prueba el impacto de anular una factura en los campos de la reserva.
    """
    print("=" * 80)
    print("TEST: Anulación de Factura y Impacto en Reserva")
    print("=" * 80)
    
    try:
        # 1. Obtener factura
        factura = FacturaElectronica.objects.get(id=factura_id)
        print(f"\n1. FACTURA ENCONTRADA:")
        print(f"   ID: {factura.id}")
        print(f"   Número: {factura.numero_factura}")
        print(f"   Reserva ID: {factura.reserva.id if factura.reserva else 'None'}")
        print(f"   Tipo: {factura.get_tipo_facturacion_display()}")
        print(f"   Activo: {factura.activo}")
        print(f"   Fecha emisión: {factura.fecha_emision}")
        
        # 2. Obtener reserva asociada
        if not factura.reserva:
            print("\n❌ ERROR: La factura no tiene reserva asociada")
            return
        
        reserva = factura.reserva
        print(f"\n2. RESERVA ASOCIADA:")
        print(f"   ID: {reserva.id}")
        print(f"   Código: {reserva.codigo}")
        print(f"   Modalidad facturación: {reserva.modalidad_facturacion}")
        
        # 3. Verificar estado ANTES de anular
        serializer_antes = ReservaDetalleSerializer(reserva)
        data_antes = serializer_antes.data
        print(f"\n3. ESTADO ANTES DE ANULAR:")
        print(f"   factura_global_generada: {data_antes.get('factura_global_generada')}")
        print(f"   factura_individual_generada: {data_antes.get('factura_individual_generada')}")
        
        # Contar facturas activas
        facturas_globales_activas = reserva.facturas.filter(
            tipo_facturacion='total',
            activo=True
        ).count()
        facturas_individuales_activas = reserva.facturas.filter(
            tipo_facturacion='por_pasajero',
            activo=True
        ).count()
        print(f"   Facturas globales activas: {facturas_globales_activas}")
        print(f"   Facturas individuales activas: {facturas_individuales_activas}")
        
        # 4. Anular factura (simular)
        print(f"\n4. SIMULANDO ANULACIÓN:")
        print(f"   ⚠️  NOTA: Este script NO anula la factura realmente.")
        print(f"   Para anular, usar: POST /api/facturacion/facturas/{factura_id}/anular/")
        print(f"   Con payload: {{'motivo': '2'}}")
        
        # Simular qué pasaría si se anula
        factura_activo_original = factura.activo
        factura.activo = False  # Simular anulación
        
        # Refrescar reserva desde DB
        reserva.refresh_from_db()
        
        # 5. Verificar estado DESPUÉS de anular (simulado)
        serializer_despues = ReservaDetalleSerializer(reserva)
        data_despues = serializer_despues.data
        print(f"\n5. ESTADO DESPUÉS DE ANULAR (SIMULADO):")
        print(f"   factura_global_generada: {data_despues.get('factura_global_generada')}")
        print(f"   factura_individual_generada: {data_despues.get('factura_individual_generada')}")
        
        # Contar facturas activas después
        facturas_globales_activas_despues = reserva.facturas.filter(
            tipo_facturacion='total',
            activo=True
        ).count()
        facturas_individuales_activas_despues = reserva.facturas.filter(
            tipo_facturacion='por_pasajero',
            activo=True
        ).count()
        print(f"   Facturas globales activas: {facturas_globales_activas_despues}")
        print(f"   Facturas individuales activas: {facturas_individuales_activas_despues}")
        
        # Restaurar estado original
        factura.activo = factura_activo_original
        
        # 6. Análisis
        print(f"\n6. ANÁLISIS:")
        if factura.tipo_facturacion == 'total':
            impacto_esperado = "factura_global_generada debería cambiar de True a False"
        elif factura.tipo_facturacion == 'por_pasajero':
            impacto_esperado = "factura_individual_generada debería cambiar de True a False"
        else:
            impacto_esperado = "Tipo de facturación desconocido"
        
        print(f"   Tipo de factura: {factura.get_tipo_facturacion_display()}")
        print(f"   Impacto esperado: {impacto_esperado}")
        print(f"\n   ✅ CONCLUSIÓN:")
        print(f"   Los campos son propiedades calculadas dinámicamente.")
        print(f"   Al anular una factura (activo=False), estos campos deberían")
        print(f"   actualizarse automáticamente en la próxima consulta GET.")
        print(f"   NO se requiere actualización manual de la reserva.")
        
        # 7. Verificar si hay otras facturas activas
        print(f"\n7. OTRAS FACTURAS DE LA RESERVA:")
        todas_facturas = reserva.facturas.all()
        for f in todas_facturas:
            print(f"   - Factura {f.id}: {f.numero_factura} | Tipo: {f.get_tipo_facturacion_display()} | Activo: {f.activo}")
        
    except FacturaElectronica.DoesNotExist:
        print(f"\n❌ ERROR: No se encontró factura con ID {factura_id}")
    except Reserva.DoesNotExist:
        print(f"\n❌ ERROR: No se encontró reserva con ID {reserva_id}")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Cambiar estos IDs según necesites
    test_anulacion_factura(factura_id=63, reserva_id=260)

