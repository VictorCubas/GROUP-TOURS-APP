from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from apps.paquete.models import Paquete
from apps.persona.models import PersonaFisica


class Reserva(models.Model):
    """
    Representa una reserva de cupos en un paquete turístico.
    Tiene un titular (responsable de la compra) y pasajeros asociados.
    """

    ESTADOS = [
        ("pendiente", "Pendiente"),     # creada, sin pago o sin pasajeros
        ("confirmada", "Confirmada"),   # seña/pago realizado, cupo asegurado
        ("incompleta", "Incompleta"),   # confirmada pero faltan datos de pasajeros
        ("finalizada", "Finalizada"),   # todo completo: pasajeros + pago
        ("cancelada", "Cancelada"),
    ]

    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Código único de la reserva"
    )
    observacion = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones adicionales sobre la reserva"
    )

    titular = models.ForeignKey(
        PersonaFisica,
        on_delete=models.PROTECT,
        related_name="reservas_titulares",
        help_text="Persona que realiza la reserva (titular de la compra)"
    )
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.PROTECT,
        related_name="reservas",
        help_text="Paquete turístico reservado"
    )
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    
    activo = models.BooleanField(default=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    cantidad_pasajeros = models.PositiveIntegerField(
        help_text="Cantidad total de pasajeros incluidos en la reserva"
    )
    monto_pagado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Monto abonado hasta el momento"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente",
        help_text="Estado actual de la reserva"
    )

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        db_table = "Reserva"

    def __str__(self):
        return f"Reserva {self.codigo} - Titular: {self.titular} ({self.paquete.nombre})"

    def save(self, *args, **kwargs):
        # Generar código único si no existe
        if not self.codigo:
            year = now().year
            last_id = Reserva.objects.filter(fecha_reserva__year=year).count() + 1
            self.codigo = f"RSV-{year}-{last_id:04d}"
        super().save(*args, **kwargs)

    @property
    def pasajeros_cargados(self):
        """Cantidad de pasajeros registrados en esta reserva"""
        return self.pasajeros.count()

    @property
    def faltan_datos_pasajeros(self):
        """Indica si faltan datos de pasajeros por cargar"""
        return self.pasajeros_cargados < self.cantidad_pasajeros

    @property
    def seña_total(self):
        """Seña total requerida según la cantidad de cupos"""
        return (self.paquete.sena or 0) * self.cantidad_pasajeros

    def puede_confirmarse(self):
        """
        Una reserva puede confirmarse si:
        - Tiene al menos un cupo
        - Se ha pagado la seña correspondiente
        """
        return self.cantidad_pasajeros > 0 and self.monto_pagado >= self.seña_total

    def actualizar_estado(self):
        """Actualiza el estado de la reserva según pago y carga de pasajeros"""
        if self.estado == "cancelada":
            return

        if self.puede_confirmarse():
            if self.faltan_datos_pasajeros:
                self.estado = "incompleta"
            else:
                self.estado = "finalizada"
        else:
            self.estado = "pendiente"

        self.save(update_fields=["estado"])

    def clean(self):
        """
        Validación de capacidad del paquete.
        Evita reservar más cupos de los disponibles.
        """
        total_ocupados = sum(
            r.cantidad_pasajeros for r in self.paquete.reservas.exclude(id=self.id)
        )
        capacidad = self.paquete.cantidad_pasajeros or 0
        if capacidad and (total_ocupados + self.cantidad_pasajeros) > capacidad:
            raise ValidationError("No hay suficientes cupos disponibles en el paquete.")


class Pasajero(models.Model):
    """
    Representa a un pasajero de una reserva.
    Puede ser el titular o un acompañante.
    """

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="pasajeros"
    )
    persona = models.ForeignKey(
        PersonaFisica,
        on_delete=models.PROTECT,
        related_name="viajes"
    )
    es_titular = models.BooleanField(
        default=False,
        help_text="Indica si este pasajero es el titular de la reserva"
    )
    ticket_numero = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Número de ticket asignado (si aplica)"
    )
    voucher_codigo = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Código de voucher asignado (si aplica)"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pasajero"
        verbose_name_plural = "Pasajeros"
        db_table = "Pasajero"

    def __str__(self):
        return f"{self.persona} - Reserva {self.reserva.codigo}"
