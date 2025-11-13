# apps/arqueo_caja/services.py
"""
Servicios y funciones utilitarias para el módulo de arqueo de caja.
Incluye integración con ComprobantePago y otras funcionalidades reutilizables.
"""
from decimal import Decimal
from django.db.models import Sum
from .models import AperturaCaja, MovimientoCaja


def obtener_caja_abierta_actual():
    """
    Retorna la apertura de caja activa más reciente.
    Útil para saber si hay una caja abierta en el sistema.

    Returns:
        AperturaCaja: La apertura activa más reciente o None
    """
    try:
        return AperturaCaja.objects.filter(
            esta_abierta=True,
            activo=True
        ).select_related('caja', 'responsable').latest('fecha_hora_apertura')
    except AperturaCaja.DoesNotExist:
        return None


def obtener_caja_abierta_por_usuario(empleado):
    """
    Busca si el empleado tiene una caja abierta.

    Args:
        empleado: Instancia de Empleado

    Returns:
        AperturaCaja: La apertura del empleado o None
    """
    try:
        return AperturaCaja.objects.filter(
            responsable=empleado,
            esta_abierta=True,
            activo=True
        ).select_related('caja').latest('fecha_hora_apertura')
    except AperturaCaja.DoesNotExist:
        return None


def mapear_comprobante_a_concepto(comprobante):
    """
    Mapea el tipo de comprobante al concepto de movimiento de caja.

    Args:
        comprobante: Instancia de ComprobantePago

    Returns:
        tuple: (tipo_movimiento, concepto)
    """
    # Mapeo de tipos de comprobante a conceptos de movimiento
    if comprobante.tipo == 'devolucion':
        return ('egreso', 'devolucion')

    # Para todos los demás (seña, pago_parcial, pago_total)
    # Mapear según el método de pago
    concepto_map = {
        'efectivo': 'venta_efectivo',
        'transferencia': 'transferencia_recibida',
        'tarjeta_debito': 'venta_tarjeta',
        'tarjeta_credito': 'venta_tarjeta',
        'cheque': 'cobro_cuenta',
        'qr': 'otro_ingreso',
        'otro': 'otro_ingreso',
    }

    concepto = concepto_map.get(comprobante.metodo_pago, 'otro_ingreso')
    return ('ingreso', concepto)


def registrar_movimiento_desde_comprobante(comprobante):
    """
    Crea un movimiento de caja a partir de un comprobante de pago.
    Solo se registra si hay una caja abierta.

    Args:
        comprobante: Instancia de ComprobantePago

    Returns:
        MovimientoCaja: El movimiento creado o None
    """
    # Buscar caja abierta actual
    apertura = obtener_caja_abierta_actual()

    if not apertura:
        # No hay caja abierta, no registrar movimiento
        return None

    # Determinar tipo y concepto
    tipo_movimiento, concepto = mapear_comprobante_a_concepto(comprobante)

    # Crear movimiento
    movimiento = MovimientoCaja.objects.create(
        apertura_caja=apertura,
        comprobante=comprobante,
        tipo_movimiento=tipo_movimiento,
        concepto=concepto,
        monto=comprobante.monto,
        metodo_pago=comprobante.metodo_pago,
        referencia=comprobante.numero_comprobante,
        descripcion=f"Pago de reserva {comprobante.reserva.codigo}",
        usuario_registro=comprobante.empleado
    )

    return movimiento


def calcular_saldo_actual_caja(apertura_caja):
    """
    Calcula el saldo actual de una caja basado en sus movimientos.

    Args:
        apertura_caja: Instancia de AperturaCaja

    Returns:
        dict: Diccionario con los totales calculados
    """
    movimientos = apertura_caja.movimientos.filter(activo=True)

    total_ingresos = movimientos.filter(
        tipo_movimiento='ingreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    total_egresos = movimientos.filter(
        tipo_movimiento='egreso'
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

    saldo = apertura_caja.monto_inicial + total_ingresos - total_egresos

    return {
        'monto_inicial': apertura_caja.monto_inicial,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'saldo_actual': saldo,
    }


def obtener_movimientos_por_metodo_pago(apertura_caja):
    """
    Agrupa los movimientos de una apertura por método de pago.

    Args:
        apertura_caja: Instancia de AperturaCaja

    Returns:
        dict: Diccionario con totales por método de pago
    """
    movimientos = apertura_caja.movimientos.filter(
        activo=True,
        tipo_movimiento='ingreso'
    )

    resultado = {}

    for metodo, nombre in MovimientoCaja.METODOS_PAGO:
        total = movimientos.filter(
            metodo_pago=metodo
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        resultado[metodo] = {
            'nombre': nombre,
            'total': total
        }

    return resultado


def validar_puede_cerrar_caja(apertura_caja):
    """
    Valida si una caja puede ser cerrada.

    Args:
        apertura_caja: Instancia de AperturaCaja

    Returns:
        tuple: (puede_cerrar: bool, mensaje_error: str)
    """
    if not apertura_caja.esta_abierta:
        return False, "La caja ya está cerrada"

    if hasattr(apertura_caja, 'cierre'):
        return False, "La caja ya tiene un cierre registrado"

    return True, None


def generar_resumen_caja_dia(fecha, caja=None):
    """
    Genera un resumen de todas las aperturas/cierres de un día específico.

    Args:
        fecha: Fecha para el resumen
        caja: (Opcional) Filtrar por una caja específica

    Returns:
        dict: Resumen del día
    """
    aperturas_query = AperturaCaja.objects.filter(
        fecha_hora_apertura__date=fecha,
        activo=True
    ).select_related('caja', 'responsable')

    if caja:
        aperturas_query = aperturas_query.filter(caja=caja)

    aperturas = list(aperturas_query)

    total_inicial = sum(a.monto_inicial for a in aperturas)
    total_movimientos = 0
    cajas_abiertas = []
    cajas_cerradas = []

    for apertura in aperturas:
        if apertura.esta_abierta:
            cajas_abiertas.append(apertura)
        else:
            cajas_cerradas.append(apertura)
            if hasattr(apertura, 'cierre'):
                total_movimientos += apertura.cierre.total_efectivo

    return {
        'fecha': fecha,
        'cantidad_aperturas': len(aperturas),
        'cajas_abiertas': len(cajas_abiertas),
        'cajas_cerradas': len(cajas_cerradas),
        'total_inicial': total_inicial,
        'total_movimientos_efectivo': total_movimientos,
        'aperturas': aperturas
    }
