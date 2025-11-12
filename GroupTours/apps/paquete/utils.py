"""
Utilidades para manejo de conversión de monedas en paquetes.
"""
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.utils import timezone


def _to_decimal(value):
    """
    Convierte un valor a Decimal de forma segura.

    Args:
        value: Valor a convertir (puede ser string, int, float, Decimal, None)

    Returns:
        Decimal: Valor convertido, o Decimal("0") si no es válido
    """
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def convertir_entre_monedas(monto, moneda_origen, moneda_destino, fecha=None):
    """
    Convierte un monto entre USD y PYG en ambas direcciones.

    Esta función maneja las conversiones bidireccionales entre dólares y guaraníes
    utilizando las cotizaciones vigentes para una fecha específica.

    Args:
        monto: Decimal/float/int - Monto a convertir
        moneda_origen: Moneda - Moneda del monto original
        moneda_destino: Moneda - Moneda a la cual convertir
        fecha: date (opcional) - Fecha para obtener cotización. Si es None, usa fecha actual.

    Returns:
        Decimal: Monto convertido a la moneda destino

    Raises:
        ValidationError: Si no existe cotización vigente para la fecha especificada
        ValidationError: Si se intenta convertir entre monedas no soportadas

    Examples:
        >>> usd = Moneda.objects.get(codigo='USD')
        >>> pyg = Moneda.objects.get(codigo='PYG')
        >>> convertir_entre_monedas(100, usd, pyg)  # 100 USD → PYG
        Decimal('730000.00')
        >>> convertir_entre_monedas(730000, pyg, usd)  # 730000 PYG → USD
        Decimal('100.00')
    """
    from apps.moneda.models import Moneda, CotizacionMoneda

    # Si las monedas son iguales, retornar el mismo monto
    if moneda_origen == moneda_destino:
        return _to_decimal(monto)

    # Usar fecha actual si no se especifica
    if fecha is None:
        fecha = timezone.now().date()

    monto_decimal = _to_decimal(monto)

    # ========== CASO 1: Convertir de USD a PYG ==========
    if moneda_origen.codigo == 'USD' and moneda_destino.codigo == 'PYG':
        cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_origen, fecha)

        if not cotizacion:
            raise ValidationError(
                f"No existe cotización de USD vigente para {fecha.strftime('%d/%m/%Y')}. "
                "Por favor registre una cotización antes de continuar."
            )

        valor_cotizacion = _to_decimal(cotizacion.valor_en_guaranies)
        return monto_decimal * valor_cotizacion

    # ========== CASO 2: Convertir de PYG a USD ==========
    if moneda_origen.codigo == 'PYG' and moneda_destino.codigo == 'USD':
        # Necesitamos la cotización de USD (cuántos guaraníes vale 1 dólar)
        moneda_usd = Moneda.objects.get(codigo='USD')
        cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha)

        if not cotizacion:
            raise ValidationError(
                f"No existe cotización de USD vigente para {fecha.strftime('%d/%m/%Y')}. "
                "Por favor registre una cotización antes de continuar."
            )

        valor_cotizacion = _to_decimal(cotizacion.valor_en_guaranies)
        return monto_decimal / valor_cotizacion

    # ========== Cualquier otra combinación no está soportada ==========
    raise ValidationError(
        f"Conversión no soportada entre {moneda_origen.codigo} y {moneda_destino.codigo}. "
        "Solo se admiten conversiones entre USD y PYG."
    )


def obtener_cotizacion_actual(moneda):
    """
    Obtiene la cotización vigente actual para una moneda.

    Args:
        moneda: Moneda - Moneda a consultar (debe ser USD)

    Returns:
        CotizacionMoneda o None si no existe cotización vigente
    """
    from apps.moneda.models import CotizacionMoneda

    if moneda.codigo == 'PYG':
        return None  # Guaraníes no tiene cotización (es la moneda base)

    return CotizacionMoneda.obtener_cotizacion_vigente(moneda)
