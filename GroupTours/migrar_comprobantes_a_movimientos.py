"""
Script de migración: Crear MovimientoCaja para ComprobantePago históricos

Este script busca todos los ComprobantePago activos que no tienen un MovimientoCaja asociado
y los procesa para crear los movimientos correspondientes cuando sea posible.

Uso:
    python migrar_comprobantes_a_movimientos.py

Opciones:
    --dry-run: Muestra qué se haría sin ejecutar cambios
    --verbose: Muestra información detallada
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GroupTours.settings')
django.setup()

from django.db import transaction
from apps.comprobante.models import ComprobantePago
from apps.arqueo_caja.models import MovimientoCaja, AperturaCaja


class MigradorComprobantes:
    """Migra ComprobantePago históricos a MovimientoCaja"""

    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            'total_comprobantes': 0,
            'ya_tienen_movimiento': 0,
            'sin_caja_abierta': 0,
            'migrados_exitosamente': 0,
            'errores': 0,
        }

    def log(self, mensaje, nivel='INFO'):
        """Imprime mensajes según el nivel de verbosidad"""
        prefijo = {
            'INFO': '✓',
            'WARNING': '⚠',
            'ERROR': '✗',
            'SUCCESS': '✅',
        }
        print(f"{prefijo.get(nivel, '•')} {mensaje}")

    def log_verbose(self, mensaje):
        """Solo imprime si verbose está activo"""
        if self.verbose:
            print(f"  → {mensaje}")

    def obtener_comprobantes_sin_movimiento(self):
        """
        Obtiene todos los ComprobantePago activos que no tienen MovimientoCaja asociado.
        """
        # Obtener todos los comprobantes activos
        todos_comprobantes = ComprobantePago.objects.filter(activo=True)
        self.stats['total_comprobantes'] = todos_comprobantes.count()

        # Filtrar los que ya tienen movimiento
        comprobantes_sin_movimiento = []
        for comprobante in todos_comprobantes:
            if MovimientoCaja.objects.filter(comprobante=comprobante).exists():
                self.stats['ya_tienen_movimiento'] += 1
            else:
                comprobantes_sin_movimiento.append(comprobante)

        return comprobantes_sin_movimiento

    def buscar_apertura_para_comprobante(self, comprobante):
        """
        Busca la apertura de caja del empleado que estaba activa en la fecha del comprobante.

        Args:
            comprobante: ComprobantePago

        Returns:
            AperturaCaja o None
        """
        # Buscar aperturas del empleado
        aperturas = AperturaCaja.objects.filter(
            responsable=comprobante.empleado,
            activo=True,
            fecha_hora_apertura__lte=comprobante.fecha_pago,
        ).order_by('-fecha_hora_apertura')

        for apertura in aperturas:
            # Si tiene cierre, verificar que el pago fue antes del cierre
            if hasattr(apertura, 'cierre') and apertura.cierre:
                if comprobante.fecha_pago <= apertura.cierre.fecha_hora_cierre:
                    return apertura
            # Si no tiene cierre, usar esta apertura
            elif apertura.esta_abierta:
                return apertura

        return None

    def mapear_metodo_pago_a_concepto(self, comprobante):
        """
        Mapea el método de pago del comprobante al concepto de MovimientoCaja.
        (Replica la lógica del modelo)
        """
        mapeo_ingreso = {
            'efectivo': 'venta_efectivo',
            'tarjeta_debito': 'venta_tarjeta',
            'tarjeta_credito': 'venta_tarjeta',
            'transferencia': 'transferencia_recibida',
            'cheque': 'otro_ingreso',
            'qr': 'otro_ingreso',
            'otro': 'otro_ingreso',
        }

        mapeo_egreso = {
            'efectivo': 'devolucion',
            'tarjeta_debito': 'devolucion',
            'tarjeta_credito': 'devolucion',
            'transferencia': 'devolucion',
            'cheque': 'devolucion',
            'qr': 'devolucion',
            'otro': 'devolucion',
        }

        if comprobante.tipo == 'devolucion':
            return mapeo_egreso.get(comprobante.metodo_pago, 'otro_egreso')

        return mapeo_ingreso.get(comprobante.metodo_pago, 'otro_ingreso')

    def crear_movimiento_para_comprobante(self, comprobante, apertura):
        """
        Crea un MovimientoCaja para un ComprobantePago.

        Args:
            comprobante: ComprobantePago
            apertura: AperturaCaja

        Returns:
            MovimientoCaja creado
        """
        # Determinar tipo de movimiento
        tipo_movimiento = 'egreso' if comprobante.tipo == 'devolucion' else 'ingreso'

        # Obtener concepto
        concepto = self.mapear_metodo_pago_a_concepto(comprobante)

        # Crear descripción
        descripcion = f"[MIGRADO] Pago de reserva {comprobante.reserva.codigo} - Comprobante {comprobante.numero_comprobante}"
        if comprobante.observaciones:
            descripcion += f"\nObs: {comprobante.observaciones}"

        # Crear el movimiento
        movimiento = MovimientoCaja(
            apertura_caja=apertura,
            comprobante=comprobante,
            tipo_movimiento=tipo_movimiento,
            concepto=concepto,
            monto=comprobante.monto,
            metodo_pago=comprobante.metodo_pago,
            referencia=comprobante.numero_comprobante,
            descripcion=descripcion,
            usuario_registro=comprobante.empleado,
        )

        # Establecer fecha del movimiento igual a la del comprobante
        movimiento.fecha_hora_movimiento = comprobante.fecha_pago

        return movimiento

    @transaction.atomic
    def migrar(self):
        """
        Ejecuta la migración completa.
        """
        self.log("=" * 70, 'INFO')
        self.log("MIGRACIÓN DE COMPROBANTES A MOVIMIENTOS DE CAJA", 'INFO')
        self.log("=" * 70, 'INFO')

        if self.dry_run:
            self.log("MODO DRY-RUN: No se realizarán cambios reales", 'WARNING')

        self.log("")

        # Obtener comprobantes sin movimiento
        self.log("Buscando comprobantes sin movimiento de caja...", 'INFO')
        comprobantes = self.obtener_comprobantes_sin_movimiento()

        self.log(f"Total de comprobantes activos: {self.stats['total_comprobantes']}", 'INFO')
        self.log(f"Comprobantes que ya tienen movimiento: {self.stats['ya_tienen_movimiento']}", 'INFO')
        self.log(f"Comprobantes a procesar: {len(comprobantes)}", 'INFO')
        self.log("")

        if not comprobantes:
            self.log("No hay comprobantes para migrar.", 'SUCCESS')
            return

        # Procesar cada comprobante
        self.log("Procesando comprobantes...", 'INFO')
        self.log("")

        for i, comprobante in enumerate(comprobantes, 1):
            self.log_verbose(f"[{i}/{len(comprobantes)}] Procesando {comprobante.numero_comprobante}...")

            try:
                # Buscar apertura correspondiente
                apertura = self.buscar_apertura_para_comprobante(comprobante)

                if not apertura:
                    self.log_verbose(f"  ⚠ Sin apertura de caja para empleado {comprobante.empleado} en fecha {comprobante.fecha_pago}")
                    self.stats['sin_caja_abierta'] += 1
                    continue

                self.log_verbose(f"  ✓ Encontrada apertura: {apertura.codigo_apertura}")

                # Crear movimiento
                if not self.dry_run:
                    movimiento = self.crear_movimiento_para_comprobante(comprobante, apertura)
                    movimiento.save()
                    self.log_verbose(f"  ✅ Movimiento creado: {movimiento.numero_movimiento}")
                else:
                    self.log_verbose(f"  [DRY-RUN] Se crearía movimiento para apertura {apertura.codigo_apertura}")

                self.stats['migrados_exitosamente'] += 1

            except Exception as e:
                self.log(f"ERROR procesando {comprobante.numero_comprobante}: {str(e)}", 'ERROR')
                self.stats['errores'] += 1

        # Resumen final
        self.log("")
        self.log("=" * 70, 'INFO')
        self.log("RESUMEN DE MIGRACIÓN", 'INFO')
        self.log("=" * 70, 'INFO')
        self.log(f"Total de comprobantes: {self.stats['total_comprobantes']}", 'INFO')
        self.log(f"Ya tenían movimiento: {self.stats['ya_tienen_movimiento']}", 'INFO')
        self.log(f"Sin caja abierta: {self.stats['sin_caja_abierta']}", 'WARNING')
        self.log(f"Migrados exitosamente: {self.stats['migrados_exitosamente']}", 'SUCCESS')
        self.log(f"Errores: {self.stats['errores']}", 'ERROR' if self.stats['errores'] > 0 else 'INFO')
        self.log("")

        if self.dry_run:
            self.log("Migración en modo DRY-RUN completada (sin cambios reales)", 'WARNING')
        else:
            self.log("Migración completada exitosamente", 'SUCCESS')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migrar ComprobantePago históricos a MovimientoCaja')
    parser.add_argument('--dry-run', action='store_true', help='Ejecutar sin hacer cambios reales')
    parser.add_argument('--verbose', action='store_true', help='Mostrar información detallada')

    args = parser.parse_args()

    migrador = MigradorComprobantes(dry_run=args.dry_run, verbose=args.verbose)
    migrador.migrar()
