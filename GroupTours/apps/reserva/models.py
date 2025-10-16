from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from apps.paquete.models import Paquete, SalidaPaquete
from apps.persona.models import PersonaFisica
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion


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
        null=True,
        blank=True,
        help_text="Persona que realiza la reserva (titular/responsable de la compra). Opcional."
    )
    paquete = models.ForeignKey(
        Paquete,
        on_delete=models.PROTECT,
        related_name="reservas",
        help_text="Paquete turístico reservado"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el servicio adicional está activo"
    )
    salida = models.ForeignKey(
        SalidaPaquete,
        on_delete=models.PROTECT,
        related_name="reservas",
        null=True,
        blank=True,
        help_text="Salida específica del paquete seleccionada por el cliente"
    )
    habitacion = models.ForeignKey(
        Habitacion,
        on_delete=models.PROTECT,
        related_name="reservas",
        null=True,
        blank=True,
        help_text="Habitación seleccionada para la reserva"
    )
    fecha_reserva = models.DateTimeField(auto_now_add=True)
    
    activo = models.BooleanField(default=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    cantidad_pasajeros = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Cantidad total de pasajeros. Si no se especifica, se toma de la capacidad de la habitación"
    )
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio acordado por pasajero al momento de la reserva (incluye habitación + ganancia/comisión + servicios base del paquete)"
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
        # Auto-completar cantidad_pasajeros si no se especificó
        if self.cantidad_pasajeros is None and self.habitacion:
            self.cantidad_pasajeros = self.habitacion.capacidad

        # Generar código único si no existe
        if not self.codigo:
            year = now().year
            last_id = Reserva.objects.filter(fecha_reserva__year=year).count() + 1
            self.codigo = f"RSV-{year}-{last_id:04d}"
        super().save(*args, **kwargs)

    @property
    def hotel(self):
        """Obtiene el hotel desde la habitación"""
        return self.habitacion.hotel if self.habitacion else None

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
        if self.salida and self.salida.senia:
            return self.salida.senia * self.cantidad_pasajeros
        return 0

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

    def calcular_precio_unitario(self):
        """
        Calcula el precio unitario por pasajero basado en:
        - Habitación específica seleccionada
        - Salida específica (ganancia/comisión)
        - Servicios incluidos en el paquete

        Retorna Decimal con el precio total por pasajero.
        """
        from decimal import Decimal

        if not self.salida or not self.habitacion:
            return Decimal("0")

        # 1. Calcular precio de la habitación por noche
        precio_habitacion = self.habitacion.precio_noche or Decimal("0")

        # 2. Calcular cantidad de noches
        if self.salida.fecha_regreso and self.salida.fecha_salida:
            noches = (self.salida.fecha_regreso - self.salida.fecha_salida).days
        else:
            noches = 1

        # 3. Precio base de la habitación por toda la estadía
        precio_habitacion_total = precio_habitacion * noches

        # 4. Sumar servicios incluidos en el paquete
        total_servicios = Decimal("0")
        for ps in self.paquete.paquete_servicios.all():
            if ps.precio and ps.precio > 0:
                total_servicios += ps.precio
            elif hasattr(ps.servicio, "precio") and ps.servicio.precio:
                total_servicios += ps.servicio.precio

        # 5. Calcular costo base total (habitación + servicios)
        costo_base_total = precio_habitacion_total + total_servicios

        # 6. Aplicar ganancia o comisión sobre el costo total
        ganancia = self.salida.ganancia or Decimal("0")
        comision = self.salida.comision or Decimal("0")

        if self.paquete.propio and ganancia > 0:
            factor = Decimal("1") + (ganancia / Decimal("100"))
        elif not self.paquete.propio and comision > 0:
            factor = Decimal("1") + (comision / Decimal("100"))
        else:
            factor = Decimal("1")

        # 7. Precio de venta por pasajero (costo base + margen)
        return costo_base_total * factor

    def clean(self):
        """
        Validación de capacidad del paquete y consistencia de salida/habitación.
        """
        # Validar que la salida pertenece al paquete
        if self.salida and self.paquete and self.salida.paquete_id != self.paquete_id:
            raise ValidationError("La salida seleccionada no pertenece al paquete elegido.")

        # Validar que el hotel de la habitación está asociado a la salida
        if self.salida and self.habitacion:
            hotel_de_habitacion = self.habitacion.hotel
            if not self.salida.hoteles.filter(id=hotel_de_habitacion.id).exists():
                raise ValidationError(
                    f"El hotel '{hotel_de_habitacion.nombre}' de la habitación seleccionada "
                    f"no está disponible para esta salida."
                )

        # Validar capacidad del paquete
        if self.cantidad_pasajeros:
            total_ocupados = sum(
                r.cantidad_pasajeros for r in self.paquete.reservas.exclude(id=self.id)
            )
            capacidad = self.paquete.cantidad_pasajeros or 0
            if capacidad and (total_ocupados + self.cantidad_pasajeros) > capacidad:
                raise ValidationError("No hay suficientes cupos disponibles en el paquete.")

    @property
    def costo_servicios_adicionales(self):
        """Suma total de todos los servicios adicionales activos"""
        return sum(
            sa.subtotal
            for sa in self.servicios_adicionales.filter(activo=True)
        )

    @property
    def precio_base_paquete(self):
        """
        Obtiene el precio unitario acordado por pasajero.
        Si no está definido, lo calcula dinámicamente basado en la habitación seleccionada.
        """
        if self.precio_unitario:
            return self.precio_unitario

        # Si no hay precio_unitario guardado, calcularlo dinámicamente
        return self.calcular_precio_unitario()

    @property
    def costo_total_estimado(self):
        """
        Costo total estimado de la reserva:
        (precio_unitario × cantidad_pasajeros) + servicios_adicionales

        NOTA: precio_unitario YA incluye habitación + ganancia + servicios base del paquete.
        Solo sumamos los servicios adicionales contratados aparte.
        """
        if not self.cantidad_pasajeros:
            return self.costo_servicios_adicionales

        costo_paquete = self.precio_base_paquete * self.cantidad_pasajeros
        return costo_paquete + self.costo_servicios_adicionales

    def listar_todos_servicios(self):
        """
        Retorna un diccionario con servicios base (del paquete) y adicionales
        """
        return {
            'base': self.paquete.paquete_servicios.all(),
            'adicionales': self.servicios_adicionales.filter(activo=True)
        }

    def agregar_servicio_adicional(self, servicio, cantidad, precio_unitario, observacion=None):
        """
        Helper method para agregar un servicio adicional a la reserva
        """
        return ReservaServiciosAdicionales.objects.create(
            reserva=self,
            servicio=servicio,
            cantidad=cantidad,
            precio_unitario=precio_unitario,
            observacion=observacion
        )


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


class ReservaServiciosAdicionales(models.Model):
    """
    Representa servicios adicionales contratados para una reserva,
    más allá de los incluidos en el paquete base.
    Pueden agregarse al momento de la reserva o posteriormente.
    """

    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.CASCADE,
        related_name="servicios_adicionales",
        help_text="Reserva a la que se agrega el servicio"
    )
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.PROTECT,
        related_name="reservas_adicionales",
        help_text="Servicio adicional contratado"
    )
    cantidad = models.PositiveIntegerField(
        default=1,
        help_text="Cantidad de personas que tomarán este servicio"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio por persona al momento de la contratación"
    )
    fecha_agregado = models.DateTimeField(
        auto_now_add=True,
        help_text="Fecha en que se agregó el servicio a la reserva"
    )
    observacion = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones sobre este servicio adicional"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Indica si el servicio adicional está activo"
    )

    class Meta:
        verbose_name = "Servicio Adicional de Reserva"
        verbose_name_plural = "Servicios Adicionales de Reserva"
        db_table = "ReservaServiciosAdicionales"
        ordering = ["-fecha_agregado"]

    def __str__(self):
        return f"{self.servicio.nombre} - Reserva {self.reserva.codigo} (x{self.cantidad})"

    @property
    def subtotal(self):
        """Calcula el subtotal del servicio adicional"""
        return self.precio_unitario * self.cantidad
