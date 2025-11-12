from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class Moneda(models.Model):
    nombre = models.CharField(max_length=50, unique=True, help_text="Nombre de la moneda. Ej: 'Dólar', 'Guaraní'")
    simbolo = models.CharField(max_length=5, help_text="Símbolo de la moneda. Ej: '$', 'Gs'")
    codigo = models.CharField(max_length=3, unique=True, help_text="Código de la moneda. Ej: 'USD', 'PYG'")
    activo = models.BooleanField(default=True, help_text="Indica si la moneda está activa")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class CotizacionMoneda(models.Model):
    """
    Registra la cotización histórica de monedas extranjeras respecto a Guaraníes.
    Se puede registrar una cotización por día. La cotización vigente para una fecha
    es la más reciente cuya fecha_vigencia sea menor o igual a esa fecha.
    """
    moneda = models.ForeignKey(
        Moneda,
        on_delete=models.PROTECT,
        related_name='cotizaciones',
        help_text="Moneda cuya cotización se registra (ej: USD)"
    )

    # Cotización: cuántos guaraníes vale 1 unidad de la moneda
    valor_en_guaranies = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Valor de 1 unidad de la moneda en guaraníes. Ej: 1 USD = 7300 Gs"
    )

    fecha_vigencia = models.DateField(
        help_text="Fecha para la cual es válida esta cotización"
    )

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    usuario_registro = models.ForeignKey(
        'usuario.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cotizaciones_registradas',
        help_text="Usuario que registró esta cotización"
    )

    observaciones = models.TextField(
        blank=True,
        null=True,
        help_text="Notas adicionales sobre esta cotización"
    )

    class Meta:
        verbose_name = "Cotización de Moneda"
        verbose_name_plural = "Cotizaciones de Monedas"
        ordering = ['-fecha_vigencia']
        # IMPORTANTE: Solo una cotización por moneda por día
        unique_together = [['moneda', 'fecha_vigencia']]
        indexes = [
            models.Index(fields=['moneda', 'fecha_vigencia']),
        ]

    def __str__(self):
        return f"{self.moneda.codigo}: {self.valor_en_guaranies} Gs ({self.fecha_vigencia})"

    def clean(self):
        """Validaciones del modelo"""
        if self.valor_en_guaranies <= 0:
            raise ValidationError("El valor de cotización debe ser mayor a cero")

        # Validar que no se registre cotización futura (opcional)
        from django.utils import timezone
        if self.fecha_vigencia > timezone.now().date():
            raise ValidationError("No se puede registrar cotización para fechas futuras")

    @classmethod
    def obtener_cotizacion_vigente(cls, moneda, fecha=None):
        """
        Obtiene la cotización vigente para una moneda en una fecha específica.
        Si no se proporciona fecha, usa la fecha actual.

        La cotización vigente es la más reciente cuya fecha_vigencia
        sea menor o igual a la fecha consultada.

        Args:
            moneda: Moneda - Moneda a consultar
            fecha: date (opcional) - Fecha para la cual se necesita la cotización.
                   Si es None, usa la fecha actual.

        Returns:
            CotizacionMoneda o None si no hay cotización disponible
        """
        from django.utils import timezone

        if fecha is None:
            fecha = timezone.now().date()

        return cls.objects.filter(
            moneda=moneda,
            fecha_vigencia__lte=fecha  # Menor o igual a la fecha consultada
        ).order_by('-fecha_vigencia').first()  # La más reciente

    @classmethod
    def convertir_a_guaranies(cls, monto, moneda, fecha=None):
        """
        Convierte un monto en la moneda especificada a guaraníes.

        Args:
            monto: Decimal - Monto a convertir
            moneda: Moneda - Moneda del monto
            fecha: date (opcional) - Fecha de referencia para la conversión

        Returns:
            Decimal - Monto convertido a guaraníes

        Raises:
            ValidationError si no hay cotización vigente para esa fecha
        """
        # Si ya está en guaraníes, retornar el mismo monto
        if moneda.codigo == 'PYG':
            return Decimal(str(monto))

        cotizacion = cls.obtener_cotizacion_vigente(moneda, fecha)

        if not cotizacion:
            from django.utils import timezone
            fecha_actual = fecha or timezone.now().date()
            fecha_str = fecha_actual.strftime('%d/%m/%Y')
            raise ValidationError(
                f"No existe cotización de {moneda.nombre} para {fecha_str}. "
                "Por favor registre una cotización antes de continuar."
            )

        monto_decimal = Decimal(str(monto))
        valor_cotizacion = Decimal(str(cotizacion.valor_en_guaranies))

        return monto_decimal * valor_cotizacion
