from decimal import Decimal

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

    MODALIDADES_FACTURACION = [
        ("global", "Facturación Global (Una factura total)"),
        ("individual", "Facturación Individual (Por pasajero)"),
    ]

    CONDICIONES_PAGO = [
        ("contado", "Contado"),
        ("credito", "Crédito"),
    ]

    MOTIVOS_CANCELACION = [
        ('1', 'Cancelación voluntaria del cliente'),
        ('2', 'Cambio de planes del cliente'),
        ('3', 'Problemas de salud'),
        ('4', 'Problemas con documentación'),
        ('5', 'Cancelación automática por falta de pago'),
        ('6', 'Fuerza mayor / Caso fortuito'),
        ('7', 'Error en la reserva'),
        ('8', 'Otro motivo'),
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
    modalidad_facturacion = models.CharField(
        max_length=20,
        choices=MODALIDADES_FACTURACION,
        null=True,
        blank=True,
        help_text="Modalidad de facturación elegida al confirmar la reserva. NULL mientras esté pendiente."
    )
    condicion_pago = models.CharField(
        max_length=20,
        choices=CONDICIONES_PAGO,
        null=True,
        blank=True,
        help_text="Condición de pago elegida al confirmar la reserva (contado o crédito). NULL mientras esté pendiente."
    )
    fecha_cancelacion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora en la que la reserva fue cancelada"
    )
    motivo_cancelacion_id = models.CharField(
        max_length=2,
        choices=MOTIVOS_CANCELACION,
        null=True,
        blank=True,
        help_text="ID del motivo de cancelación"
    )
    motivo_cancelacion = models.TextField(
        null=True,
        blank=True,
        help_text="Observaciones adicionales sobre la cancelación"
    )
    cupos_liberados = models.BooleanField(
        default=False,
        help_text="Indica si los cupos asociados a la reserva ya fueron liberados"
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
            self.cantidad_pasajeros = self.habitacion.tipo_habitacion.capacidad

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
            capacidad_pasajeros = self.habitacion.tipo_habitacion.capacidad

            # 3. Actualizar CupoHabitacionSalida (descontar habitaciones disponibles)
            cupo_hab_salida = CupoHabitacionSalida.objects.filter(
                salida=self.salida,
                habitacion=self.habitacion
            ).first()

            if cupo_hab_salida:
                # Verificar que hay cupo suficiente de habitaciones
                if cupo_hab_salida.cupo < cantidad_habitaciones:
                    raise ValueError(
                        f"No hay suficiente cupo disponible para la habitación '{self.habitacion.tipo_habitacion.nombre}'. "
                        f"Disponibles: {cupo_hab_salida.cupo}, Solicitadas: {cantidad_habitaciones}"
                    )
                # Decrementar el cupo de la habitación
                cupo_hab_salida.cupo -= cantidad_habitaciones
                cupo_hab_salida.save(update_fields=['cupo'])
            else:
                raise ValueError(
                    f"No se encontró configuración de cupo para la habitación '{self.habitacion.tipo_habitacion.nombre}' "
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
    def dias_hasta_salida(self):
        """
        Retorna la cantidad de días que faltan para la fecha de salida.
        Si no hay salida asociada, retorna None.
        """
        if not self.salida or not self.salida.fecha_salida:
            return None
        return (self.salida.fecha_salida - now().date()).days

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
        from decimal import Decimal
        if self.salida and self.salida.senia and self.cantidad_pasajeros:
            return self.salida.senia * self.cantidad_pasajeros
        return Decimal("0")

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
        # IMPORTANTE: Usar .all() en lugar de acceder directamente para evitar caché
        pasajeros_reales = self.pasajeros.all().exclude(persona__documento__contains='_PEND')

        if not pasajeros_reales.exists():
            return False

        # Verificar que TODOS los pasajeros reales estén totalmente pagados
        for pasajero in pasajeros_reales:
            if not pasajero.esta_totalmente_pagado:
                return False

        return True

    def calcular_montos_cancelacion(self):
        """
        Calcula los montos involucrados al cancelar una reserva.
        Returns:
            dict con monto_sena, monto_pagos_adicionales y monto_reembolsable.
        """
        from django.db.models import Sum

        comprobantes_activos = self.comprobantes.filter(activo=True)

        monto_sena = comprobantes_activos.filter(tipo='sena').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0')

        monto_pagos_adicionales = comprobantes_activos.filter(
            tipo__in=['pago_parcial', 'pago_total']
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        monto_devoluciones = comprobantes_activos.filter(
            tipo='devolucion'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')

        monto_reembolsable = max(monto_pagos_adicionales - monto_devoluciones, Decimal('0'))

        return {
            'monto_sena': monto_sena,
            'monto_pagos_adicionales': monto_pagos_adicionales,
            'monto_reembolsable': monto_reembolsable,
        }

    def liberar_cupo(self, forzar=False):
        """
        Libera el cupo asociado a la reserva solo para paquetes propios.
        """
        if self.cupos_liberados and not forzar:
            return

        if not self.paquete or not self.paquete.propio:
            return

        if not self.salida:
            return

        cupo_actualizado = False

        if self.habitacion:
            cupo_hab_salida = CupoHabitacionSalida.objects.filter(
                salida=self.salida,
                habitacion=self.habitacion
            ).first()

            if cupo_hab_salida:
                cupo_hab_salida.cupo += 1
                cupo_hab_salida.save(update_fields=['cupo'])
                cupo_actualizado = True

            if self.salida.cupo is not None:
                capacidad = self.habitacion.tipo_habitacion.capacidad or self.cantidad_pasajeros or 0
                if capacidad > 0:
                    self.salida.cupo += capacidad
                    self.salida.save(update_fields=['cupo'])
                    cupo_actualizado = True

        if cupo_actualizado:
            self.cupos_liberados = True
            self.save(update_fields=['cupos_liberados'])

    def marcar_cancelada(self, motivo_cancelacion_id=None, motivo_observaciones=None, liberar_cupo=True):
        """
        Cambia el estado de la reserva a cancelada, registra motivo/fecha
        y libera cupos si corresponde.
        
        Args:
            motivo_cancelacion_id: ID del motivo (choice definido en MOTIVOS_CANCELACION)
            motivo_observaciones: Observaciones adicionales sobre la cancelación
            liberar_cupo: Si debe liberar los cupos (True por defecto)
        """
        if self.estado == "cancelada":
            return False

        self.estado = "cancelada"
        self.motivo_cancelacion_id = motivo_cancelacion_id or '8'  # '8' = Otro motivo
        self.motivo_cancelacion = motivo_observaciones or ""
        self.fecha_cancelacion = now()
        self.datos_completos = False
        self.save(update_fields=[
            'estado', 'motivo_cancelacion_id', 'motivo_cancelacion', 
            'fecha_cancelacion', 'datos_completos'
        ])

        if liberar_cupo:
            self.liberar_cupo()

        return True

    def actualizar_estado(self, modalidad_facturacion=None, condicion_pago=None):
        """
        Actualiza el estado de la reserva según pago y carga de pasajeros.
        Soporta tanto transiciones hacia adelante como hacia atrás (retroceso).

        Args:
            modalidad_facturacion: 'global' o 'individual' (requerido al confirmar desde pendiente)
            condicion_pago: 'contado' o 'credito' (requerido al confirmar desde pendiente)

        Lógica de estados (con soporte de retroceso):

        - Pendiente: Sin pago o pago insuficiente para la seña
          → AVANCE a confirmada: si puede_confirmarse() (seña completa)

        - Confirmada: Seña pagada (o más, pero < 100%), cupo asegurado
          - datos_completos=True si todos los pasajeros están cargados
          - datos_completos=False si faltan datos de pasajeros
          - Al pasar a confirmada desde pendiente, se debe definir modalidad_facturacion Y condicion_pago
          → AVANCE a finalizada: si esta_totalmente_pagada() Y datos_completos
          → RETROCESO a pendiente: si ya NO puede_confirmarse() (ej: NC redujo pago < seña)

        - Finalizada: Pago total completo (100%) Y todos los pasajeros reales cargados
          → RETROCESO a confirmada: si ya NO esta_totalmente_pagada() PERO puede_confirmarse()
          → RETROCESO a pendiente: si ya NO esta_totalmente_pagada() Y NO puede_confirmarse()
          (Retroceso ocurre típicamente por Notas de Crédito que reducen monto_pagado)

        - Cancelada: Reserva cancelada (estado manual, NO cambia automáticamente)

        El campo 'datos_completos' indica si todos los pasajeros están cargados.

        IMPORTANTE: Una Nota de Crédito del 100% NO pasa la reserva a "cancelada" automáticamente.
        El estado "cancelada" es una decisión de negocio que se establece manualmente.
        """
        if self.estado == "cancelada":
            return

        # Actualizar flag de datos completos
        self.datos_completos = not self.faltan_datos_pasajeros

        # Estado actual: pendiente
        if self.estado == "pendiente":
            if self.puede_confirmarse():  # seña total pagada
                # Al confirmar, DEBE definir modalidad Y condición de pago si aún NO están definidas
                # Si la reserva ya tiene modalidad y condición, usar esas
                modalidad_a_usar = modalidad_facturacion or self.modalidad_facturacion
                condicion_a_usar = condicion_pago or self.condicion_pago

                if modalidad_a_usar is None:
                    raise ValidationError(
                        "Debe seleccionar la modalidad de facturación al confirmar la reserva. "
                        "Opciones: 'global' (una factura total) o 'individual' (factura por pasajero)"
                    )

                if modalidad_a_usar not in ['global', 'individual']:
                    raise ValidationError(
                        "Modalidad inválida. Use 'global' o 'individual'"
                    )

                if condicion_a_usar is None:
                    raise ValidationError(
                        "Debe seleccionar la condición de pago al confirmar la reserva. "
                        "Opciones: 'contado' o 'credito'"
                    )

                if condicion_a_usar not in ['contado', 'credito']:
                    raise ValidationError(
                        "Condición de pago inválida. Use 'contado' o 'credito'"
                    )

                # Validación: Si es facturación individual, NO puede ser crédito
                if modalidad_a_usar == 'individual' and condicion_a_usar == 'credito':
                    raise ValidationError(
                        "Las facturas a crédito solo están disponibles para facturación global. "
                        "Si desea crédito, seleccione modalidad 'global'."
                    )

                # Establecer modalidad y condición (FIJO después de esto)
                self.modalidad_facturacion = modalidad_a_usar
                self.condicion_pago = condicion_a_usar
                self.estado = "confirmada"
                self.save(update_fields=["estado", "datos_completos", "modalidad_facturacion", "condicion_pago"])
                return

        # Estado actual: confirmada
        elif self.estado == "confirmada":
            # NO permitir cambiar modalidad ni condición de pago
            if modalidad_facturacion is not None and modalidad_facturacion != self.modalidad_facturacion:
                raise ValidationError(
                    f"No se puede cambiar la modalidad de facturación. "
                    f"Ya está definida como '{self.modalidad_facturacion}'"
                )

            if condicion_pago is not None and condicion_pago != self.condicion_pago:
                raise ValidationError(
                    f"No se puede cambiar la condición de pago. "
                    f"Ya está definida como '{self.condicion_pago}'"
                )

            # RETROCESO: Si ya NO puede confirmarse (ej: NC redujo el pago debajo de la seña)
            if not self.puede_confirmarse():
                self.estado = "pendiente"
                self.save(update_fields=["estado", "datos_completos"])
                return

            # AVANCE: Transición a 'finalizada'
            # DEBUG: Agregar logging para diagnóstico
            esta_pagada = self.esta_totalmente_pagada()
            datos_ok = self.datos_completos

            print(f"[DEBUG] Reserva {self.id}: estado={self.estado}, esta_totalmente_pagada={esta_pagada}, datos_completos={datos_ok}")

            if esta_pagada and datos_ok:
                # Pago total completo (100%) + todos los pasajeros cargados
                print(f"[DEBUG] Reserva {self.id}: Cambiando estado a FINALIZADA")
                self.estado = "finalizada"
                self.save(update_fields=["estado", "datos_completos"])
                print(f"[DEBUG] Reserva {self.id}: Estado guardado como {self.estado}")
                return
            else:
                print(f"[DEBUG] Reserva {self.id}: NO cumple condiciones para finalizar")

        # Estado actual: finalizada
        elif self.estado == "finalizada":
            # RETROCESO: Si ya NO está totalmente pagada (ej: NC redujo el monto_pagado)
            if not self.esta_totalmente_pagada():
                # Determinar a qué estado retroceder
                if self.puede_confirmarse():
                    # Aún tiene seña completa -> retroceder a CONFIRMADA
                    self.estado = "confirmada"
                else:
                    # No tiene seña completa -> retroceder a PENDIENTE
                    self.estado = "pendiente"
                self.save(update_fields=["estado", "datos_completos"])
                return

        # Guardar cambios sin cambio de estado
        self.save(update_fields=["datos_completos"])

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

            # 1.1 Convertir a la moneda de la salida si difieren
            if self.habitacion.moneda != self.salida.moneda:
                from apps.paquete.utils import convertir_entre_monedas
                precio_habitacion = convertir_entre_monedas(
                    monto=precio_habitacion,
                    moneda_origen=self.habitacion.moneda,
                    moneda_destino=self.salida.moneda,
                    fecha=self.salida.fecha_salida
                )

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
        from decimal import Decimal
        total = sum(
            sa.subtotal
            for sa in self.servicios_adicionales.filter(activo=True)
        )
        return Decimal(str(total)) if total else Decimal("0")

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
        from decimal import Decimal
        
        if not self.cantidad_pasajeros:
            return self.costo_servicios_adicionales

        costo_paquete = self.precio_base_paquete * self.cantidad_pasajeros
        return costo_paquete + self.costo_servicios_adicionales

    @property
    def monto_pagado(self):
        """
        Monto total pagado en la reserva, calculado sumando el monto_pagado de todos los pasajeros.

        IMPORTANTE: Esta propiedad sobrescribe el campo monto_pagado del modelo.
        El campo en la BD se mantiene por compatibilidad pero ya NO se actualiza.
        El valor real siempre se calcula dinámicamente desde los pasajeros.

        Esto garantiza que las Notas de Crédito se reflejen automáticamente,
        ya que Pasajero.monto_pagado ya las considera.
        """
        from decimal import Decimal
        return sum(
            pasajero.monto_pagado
            for pasajero in self.pasajeros.all()
        ) or Decimal("0")

    @property
    def saldo_pendiente(self):
        """Saldo pendiente de la reserva"""
        return self.costo_total_estimado - self.monto_pagado

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
    por_asignar = models.BooleanField(
        default=False,
        help_text="Indica si este pasajero está pendiente de asignación (True) o tiene datos reales (False)"
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
        from decimal import Decimal
        
        # Auto-asignar precio si no está definido (tomar el precio_unitario de la reserva)
        if self.precio_asignado is None and self.reserva:
            # Intentar obtener precio_unitario de la reserva, sino usar precio_base_paquete
            if self.reserva.precio_unitario:
                self.precio_asignado = self.reserva.precio_unitario
            else:
                # Fallback: usar precio_base_paquete (que calcula dinámicamente si es necesario)
                self.precio_asignado = self.reserva.precio_base_paquete or Decimal("0")

        super().save(*args, **kwargs)

    @property
    def monto_pagado(self):
        """
        Suma de todas las distribuciones de pago asociadas a este pasajero,
        menos las notas de crédito que NO tienen distribución de devolución.

        ENFOQUE HÍBRIDO:
        1. Suma todas las distribuciones (incluyendo devoluciones con monto negativo)
        2. Resta las NC que NO tienen un comprobante de devolución asociado
           (esto cubre casos donde el signal no se ejecutó)

        Solo cuenta comprobantes activos (no anulados) y NC activas.

        NOTA: Las NC reducen el monto efectivamente pagado por el pasajero,
        ya que representan devoluciones o acreditaciones de dinero.

        PROTECCIÓN: El monto pagado nunca será menor a 0, para evitar errores
        cuando hay facturas mal generadas con NC incorrectas.
        """
        from decimal import Decimal
        from apps.comprobante.models import ComprobantePago

        # 1. Suma de TODAS las distribuciones (incluyendo devoluciones con monto negativo)
        total_pagos = sum(
            d.monto
            for d in self.distribuciones_pago.filter(comprobante__activo=True)
        )
        
        # Convertir a Decimal si sum retornó un int (lista vacía)
        total_pagos_decimal = Decimal(str(total_pagos)) if total_pagos else Decimal("0")

        # 2. Restar las NC que NO tienen comprobante de devolución asociado
        from apps.facturacion.models import NotaCreditoElectronica
        total_nc_sin_distribucion = Decimal("0")

        for factura in self.facturas.filter(activo=True):
            for nc in factura.notas_credito.filter(activo=True):
                # Verificar si esta NC ya tiene un comprobante de devolución
                tiene_comprobante_devolucion = ComprobantePago.objects.filter(
                    reserva=self.reserva,
                    tipo='devolucion',
                    referencia=f"NC: {nc.numero_nota_credito}",
                    activo=True
                ).exists()

                # Si NO tiene comprobante de devolución, restar la NC manualmente
                if not tiene_comprobante_devolucion:
                    total_nc_sin_distribucion += nc.total_general

        # Monto pagado efectivo = distribuciones (con devoluciones negativas) - NC sin distribución
        monto_final = total_pagos_decimal - total_nc_sin_distribucion

        # PROTECCIÓN: El monto pagado no puede ser negativo
        # Esto previene errores cuando hay facturas mal generadas con NC incorrectas
        return max(monto_final, Decimal("0"))

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
        from decimal import Decimal, InvalidOperation
        if not self.precio_asignado or self.precio_asignado == 0:
            return Decimal("0")
        
        try:
            porcentaje = (self.monto_pagado / self.precio_asignado) * Decimal("100")
            return round(porcentaje, 2)
        except (InvalidOperation, ZeroDivisionError):
            return Decimal("0")

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
