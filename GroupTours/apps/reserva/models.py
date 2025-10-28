from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from apps.paquete.models import CupoHabitacionSalida, Paquete, SalidaPaquete
from apps.persona.models import PersonaFisica
from apps.servicio.models import Servicio
from apps.hotel.models import Hotel, Habitacion


class Reserva(models.Model):
    """
    Representa una reserva de cupos en un paquete turístico.
    Tiene un titular (responsable de la compra) y pasajeros asociados.
    """

    ESTADOS = [
        ("pendiente", "Pendiente"),                    # creada, sin pago o sin pasajeros
        ("confirmada", "Confirmado"),                  # seña/pago realizado, cupo asegurado
        ("finalizada", "Finalizado"),                  # pago total completo + datos completos
        ("cancelada", "Cancelado"),
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
        help_text="Persona que realiza la reserva (titular/responsable de la compra). Requerido al crear nuevas reservas."
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
    datos_completos = models.BooleanField(
        default=False,
        help_text="Indica si todos los datos de pasajeros están cargados"
    )

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        db_table = "Reserva"

    def __str__(self):
        return f"Reserva {self.codigo} - Titular: {self.titular} ({self.paquete.nombre})"

    def save(self, *args, **kwargs):
        es_nueva = self._state.adding  # True si la reserva aún no fue guardada

        # Auto-completar cantidad_pasajeros si no se especificó
        if self.cantidad_pasajeros is None and self.habitacion:
            self.cantidad_pasajeros = self.habitacion.capacidad

        # Generar código único si no existe
        if not self.codigo:
            year = now().year
            last_id = Reserva.objects.filter(fecha_reserva__year=year).count() + 1
            self.codigo = f"RSV-{year}-{last_id:04d}"

        # DESCUENTO DE CUPOS - SOLO PARA PAQUETES PROPIOS
        # Para paquetes de distribuidora, los cupos están sujetos a verificación externa
        if es_nueva and self.salida and self.habitacion and self.paquete.propio:
            # 1. Determinar cantidad de habitaciones (siempre 1 por reserva)
            cantidad_habitaciones = 1

            # 2. Determinar capacidad de pasajeros (de la habitación)
            capacidad_pasajeros = self.habitacion.capacidad

            # 3. Actualizar CupoHabitacionSalida (descontar habitaciones disponibles)
            cupo_hab_salida = CupoHabitacionSalida.objects.filter(
                salida=self.salida,
                habitacion=self.habitacion
            ).first()

            if cupo_hab_salida:
                # Verificar que hay cupo suficiente de habitaciones
                if cupo_hab_salida.cupo < cantidad_habitaciones:
                    raise ValueError(
                        f"No hay suficiente cupo disponible para la habitación '{self.habitacion.numero}'. "
                        f"Disponibles: {cupo_hab_salida.cupo}, Solicitadas: {cantidad_habitaciones}"
                    )
                # Decrementar el cupo de la habitación
                cupo_hab_salida.cupo -= cantidad_habitaciones
                cupo_hab_salida.save(update_fields=['cupo'])
            else:
                raise ValueError(
                    f"No se encontró configuración de cupo para la habitación '{self.habitacion.numero}' "
                    f"en la salida seleccionada."
                )

            # 4. Actualizar SalidaPaquete.cupo (descontar capacidad de pasajeros)
            if self.salida.cupo is not None:
                if self.salida.cupo < capacidad_pasajeros:
                    raise ValueError(
                        f"No hay suficiente cupo de pasajeros en la salida. "
                        f"Disponibles: {self.salida.cupo}, Solicitados: {capacidad_pasajeros}"
                    )
                self.salida.cupo -= capacidad_pasajeros
                self.salida.save(update_fields=['cupo'])


        super().save(*args, **kwargs)


    @property
    def hotel(self):
        """Obtiene el hotel desde la habitación"""
        return self.habitacion.hotel if self.habitacion else None

    @property
    def pasajeros_cargados(self):
        """
        Cantidad de pasajeros REALES registrados en esta reserva.
        Excluye pasajeros pendientes (aquellos con documento que termina en _PEND).
        """
        return self.pasajeros.exclude(persona__documento__contains='_PEND').count()

    @property
    def faltan_datos_pasajeros(self):
        """
        Indica si faltan datos de pasajeros por cargar.
        Solo cuenta pasajeros reales (excluye pendientes con _PEND).
        """
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
        - Se ha pagado la seña total requerida

        Si faltan datos de pasajeros reales,
        valida a nivel de reserva total comparando monto_pagado vs seña_total.

        Si todos los pasajeros reales están cargados,
        valida que TODOS los pasajeros tengan su seña completa pagada individualmente.
        """
        # Si faltan datos de pasajeros reales, validar a nivel reserva total
        if self.faltan_datos_pasajeros:
            return self.cantidad_pasajeros > 0 and self.monto_pagado >= self.seña_total

        # Si todos los pasajeros reales están cargados, validar individualmente
        # Excluir pasajeros pendientes de la validación individual
        pasajeros_reales = self.pasajeros.exclude(persona__documento__contains='_PEND')
        return pasajeros_reales.exists() and all(pasajero.tiene_sena_pagada for pasajero in pasajeros_reales)

    def esta_totalmente_pagada(self):
        """
        Verifica si se ha pagado el costo total estimado de la reserva.

        Si faltan datos de pasajeros reales,
        valida a nivel de reserva total comparando monto_pagado vs costo_total_estimado.

        Si todos los pasajeros reales están cargados,
        valida que TODOS los pasajeros reales tengan saldo_pendiente = 0.
        """
        # Si faltan datos de pasajeros reales, validar a nivel reserva total
        if self.faltan_datos_pasajeros:
            return self.monto_pagado >= self.costo_total_estimado

        # Si todos los pasajeros reales están cargados, validar individualmente
        # Excluir pasajeros pendientes de la validación individual
        pasajeros_reales = self.pasajeros.exclude(persona__documento__contains='_PEND')
        return pasajeros_reales.exists() and all(pasajero.esta_totalmente_pagado for pasajero in pasajeros_reales)

    def actualizar_estado(self):
        """
        Actualiza el estado de la reserva según pago y carga de pasajeros.

        Lógica de estados:
        - Pendiente: Sin pago o pago insuficiente para la seña
        - Confirmada: Seña pagada (o más, pero < 100%), cupo asegurado
          - datos_completos=True si todos los pasajeros están cargados
          - datos_completos=False si faltan datos de pasajeros
        - Finalizada: Pago total completo (100%) Y todos los pasajeros reales cargados
        - Cancelada: Reserva cancelada

        El campo 'datos_completos' indica si todos los pasajeros están cargados.
        """
        if self.estado == "cancelada":
            return

        # Actualizar flag de datos completos
        self.datos_completos = not self.faltan_datos_pasajeros

        # Actualizar estado según pago y datos de pasajeros
        if self.esta_totalmente_pagada() and self.datos_completos:
            # Pago total completo (100%) + todos los pasajeros cargados
            self.estado = "finalizada"
        elif self.puede_confirmarse():
            # Seña pagada (puede ser parcial o total, pero si no cumple condición anterior, no es finalizada)
            self.estado = "confirmada"
        else:
            # Sin pago suficiente para la seña
            self.estado = "pendiente"

        self.save(update_fields=["estado", "datos_completos"])

    @property
    def estado_display(self):
        """
        Retorna un texto descriptivo del estado incluyendo datos completos y estado de pago.
        Útil para mostrar en UI.

        Para estado "confirmada":
        - "Confirmado Completo": Pago total completo (100%) + Todos los pasajeros cargados
        - "Confirmado Incompleto": Cualquier otro caso (pago parcial, faltan pasajeros, o ambos)
        """
        estados_base = {
            "pendiente": "Pendiente de seña",
            "confirmada": "Confirmado",
            "finalizada": "Finalizado",
            "cancelada": "Cancelado",
        }

        estado_texto = estados_base.get(self.estado, self.estado.capitalize())

        # Agregar información de completitud si está confirmada
        if self.estado == "confirmada":
            # "Completo" solo si: pago total completo (100%) Y todos los pasajeros cargados
            if self.esta_totalmente_pagada() and self.datos_completos:
                return f"{estado_texto} Completo"
            else:
                # "Incompleto" si: falta pago O faltan pasajeros O ambos
                return f"{estado_texto} Incompleto"

        return estado_texto

    def calcular_precio_unitario(self):
        """
        Calcula el precio unitario por pasajero basado en:
        - Para paquetes de distribuidora: precio de catálogo + comisión
        - Para paquetes propios: habitación + servicios + ganancia

        Retorna Decimal con el precio total por pasajero.
        """
        from decimal import Decimal
        from apps.paquete.models import PrecioCatalogoHabitacion, PrecioCatalogoHotel

        if not self.salida or not self.habitacion:
            return Decimal("0")

        # === PAQUETES DE DISTRIBUIDORA ===
        # Usar precios de catálogo de la distribuidora
        if not self.paquete.propio:
            # 1. Buscar precio específico de la habitación (prioridad)
            precio_catalogo_hab = PrecioCatalogoHabitacion.objects.filter(
                salida=self.salida,
                habitacion=self.habitacion
            ).first()

            if precio_catalogo_hab:
                precio_base = precio_catalogo_hab.precio_catalogo
            else:
                # 2. Buscar precio a nivel de hotel
                precio_catalogo_hotel = PrecioCatalogoHotel.objects.filter(
                    salida=self.salida,
                    hotel=self.habitacion.hotel
                ).first()

                if precio_catalogo_hotel:
                    precio_base = precio_catalogo_hotel.precio_catalogo
                else:
                    # 3. Fallback: usar precio_noche de la habitación × noches
                    precio_habitacion = self.habitacion.precio_noche or Decimal("0")
                    if self.salida.fecha_regreso and self.salida.fecha_salida:
                        noches = (self.salida.fecha_regreso - self.salida.fecha_salida).days
                    else:
                        noches = 1
                    precio_base = precio_habitacion * noches

            # 4. Aplicar comisión sobre el precio base del catálogo
            comision = self.salida.comision or Decimal("0")
            if comision > 0:
                factor = Decimal("1") + (comision / Decimal("100"))
                return precio_base * factor
            else:
                return precio_base

        # === PAQUETES PROPIOS ===
        # Calcular desde habitación + servicios + ganancia
        else:
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

            # 6. Aplicar ganancia sobre el costo total
            ganancia = self.salida.ganancia or Decimal("0")
            if ganancia > 0:
                factor = Decimal("1") + (ganancia / Decimal("100"))
                return costo_base_total * factor
            else:
                return costo_base_total

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

        # Validar capacidad del paquete - SOLO PARA PAQUETES PROPIOS
        # Para distribuidoras, la capacidad se verifica externamente
        if self.paquete.propio and self.cantidad_pasajeros:
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
    precio_asignado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Precio acordado para este pasajero (normalmente precio_unitario de la reserva)"
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

    def save(self, *args, **kwargs):
        # Auto-asignar precio si no está definido (tomar el precio_unitario de la reserva)
        if self.precio_asignado is None and self.reserva and self.reserva.precio_unitario:
            self.precio_asignado = self.reserva.precio_unitario

        super().save(*args, **kwargs)

    @property
    def monto_pagado(self):
        """
        Suma de todas las distribuciones de pago asociadas a este pasajero.
        Solo cuenta comprobantes activos (no anulados).
        """
        from decimal import Decimal
        total = sum(
            d.monto
            for d in self.distribuciones_pago.filter(comprobante__activo=True)
        )
        return total if total else Decimal("0")

    @property
    def saldo_pendiente(self):
        """
        Saldo que le falta pagar a este pasajero.
        """
        from decimal import Decimal
        if not self.precio_asignado:
            return Decimal("0")
        return self.precio_asignado - self.monto_pagado

    @property
    def porcentaje_pagado(self):
        """
        Porcentaje del precio que ha sido pagado por este pasajero.
        Retorna valor entre 0 y 100.
        """
        from decimal import Decimal
        if not self.precio_asignado or self.precio_asignado == 0:
            return Decimal("0")
        porcentaje = (self.monto_pagado / self.precio_asignado) * Decimal("100")
        return round(porcentaje, 2)

    @property
    def seña_requerida(self):
        """
        Monto de seña requerido para este pasajero.
        La seña es un MONTO FIJO por pasajero definido en SalidaPaquete.senia
        """
        from decimal import Decimal
        if not self.reserva or not self.reserva.salida:
            return Decimal("0")

        # Retornar el monto fijo de seña de la salida
        return self.reserva.salida.senia or Decimal("0")

    @property
    def tiene_sena_pagada(self):
        """
        Indica si este pasajero tiene su seña completa pagada.
        """
        return self.monto_pagado >= self.seña_requerida

    @property
    def esta_totalmente_pagado(self):
        """
        Indica si este pasajero tiene el 100% de su precio pagado.
        """
        return self.saldo_pendiente <= 0


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
