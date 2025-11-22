"""
Serializers específicos para reportes detallados.
Optimizados para lectura y exportación.
"""
from rest_framework import serializers
from apps.arqueo_caja.models import MovimientoCaja
from apps.reserva.models import Reserva
from apps.paquete.models import Paquete
from decimal import Decimal


# ============================================================================
# MOVIMIENTOS DE CAJA
# ============================================================================

class MovimientoCajaReporteSerializer(serializers.ModelSerializer):
    """
    Serializer para reporte de movimientos de caja.
    Incluye campos anidados y valores display.
    """
    # Campos de la caja
    caja_nombre = serializers.CharField(source='apertura_caja.caja.nombre', read_only=True)
    caja_numero = serializers.IntegerField(source='apertura_caja.caja.id', read_only=True)
    
    # Campos display (legibles)
    tipo_movimiento_display = serializers.CharField(source='get_tipo_movimiento_display', read_only=True)
    concepto_display = serializers.SerializerMethodField()
    metodo_pago_display = serializers.CharField(source='get_metodo_pago_display', read_only=True)
    
    # Usuario que registró
    usuario_registro = serializers.SerializerMethodField()
    
    # Comprobante
    comprobante_numero = serializers.SerializerMethodField()
    
    # Fecha formateada
    fecha_hora = serializers.DateTimeField(source='fecha_hora_movimiento', read_only=True)
    
    # Montos en ambas monedas
    monto_gs = serializers.SerializerMethodField()
    monto_usd = serializers.SerializerMethodField()
    moneda_original = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoCaja
        fields = [
            'id',
            'numero_movimiento',
            'fecha_hora',
            'caja_nombre',
            'caja_numero',
            'tipo_movimiento',
            'tipo_movimiento_display',
            'concepto',
            'concepto_display',
            'descripcion',
            'monto',
            'monto_gs',
            'monto_usd',
            'moneda_original',
            'metodo_pago',
            'metodo_pago_display',
            'referencia',
            'usuario_registro',
            'comprobante_numero',
        ]
    
    def get_concepto_display(self, obj):
        """Obtener el texto legible del concepto"""
        conceptos_dict = dict(MovimientoCaja.CONCEPTOS_INGRESO + MovimientoCaja.CONCEPTOS_EGRESO)
        return conceptos_dict.get(obj.concepto, obj.concepto)
    
    def get_usuario_registro(self, obj):
        """Nombre completo del usuario que registró"""
        if obj.usuario_registro and obj.usuario_registro.persona:
            # Usar __str__() del modelo Persona que ya concatena nombre y apellido
            return str(obj.usuario_registro.persona)
        return "N/A"
    
    def get_comprobante_numero(self, obj):
        """Número del comprobante si existe"""
        if obj.comprobante:
            return obj.comprobante.numero_comprobante
        return None
    
    def get_monto_gs(self, obj):
        """
        Monto en guaraníes.
        Detecta la moneda real del movimiento desde comprobante → reserva → paquete.
        """
        from apps.moneda.models import CotizacionMoneda
        
        # Intentar obtener la moneda del comprobante asociado
        moneda_codigo = None
        if obj.comprobante and obj.comprobante.reserva and obj.comprobante.reserva.paquete:
            moneda_obj = obj.comprobante.reserva.paquete.moneda
            if moneda_obj:
                moneda_codigo = moneda_obj.codigo
        
        # Si no hay moneda o es PYG, el monto ya está en Gs
        if not moneda_codigo or moneda_codigo == 'PYG':
            return float(obj.monto)
        
        # Si el monto está en otra moneda, convertir a Gs
        try:
            moneda_obj = obj.comprobante.reserva.paquete.moneda
            monto_gs = CotizacionMoneda.convertir_a_guaranies(obj.monto, moneda_obj)
            return float(monto_gs)
        except Exception:
            # Si falla la conversión, asumir que ya está en Gs
            return float(obj.monto)
    
    def get_monto_usd(self, obj):
        """
        Monto convertido a dólares usando la cotización vigente.
        Detecta la moneda real del movimiento desde comprobante → reserva → paquete.
        """
        from apps.moneda.models import Moneda, CotizacionMoneda
        
        try:
            # Intentar obtener la moneda del comprobante asociado
            moneda_codigo = None
            if obj.comprobante and obj.comprobante.reserva and obj.comprobante.reserva.paquete:
                moneda_obj = obj.comprobante.reserva.paquete.moneda
                if moneda_obj:
                    moneda_codigo = moneda_obj.codigo
            
            # Si el monto ya está en USD, retornarlo directamente
            if moneda_codigo == 'USD':
                return float(obj.monto)
            
            # Si está en Gs o sin moneda, convertir a USD
            moneda_usd = Moneda.objects.get(codigo='USD')
            fecha_movimiento = obj.fecha_hora_movimiento.date()
            cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd, fecha_movimiento)
            
            if cotizacion and cotizacion.valor_en_guaranies > 0:
                # Si el monto está en Gs o sin moneda definida
                if not moneda_codigo or moneda_codigo == 'PYG':
                    monto_usd = Decimal(str(obj.monto)) / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(monto_usd, 2))
                else:
                    # Si está en otra moneda, primero convertir a Gs, luego a USD
                    moneda_obj = obj.comprobante.reserva.paquete.moneda
                    monto_gs = CotizacionMoneda.convertir_a_guaranies(obj.monto, moneda_obj)
                    monto_usd = monto_gs / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(monto_usd, 2))
            
            return None
            
        except (Moneda.DoesNotExist, Exception):
            return None
    
    def get_moneda_original(self, obj):
        """
        Detecta la moneda original del movimiento.
        Si tiene comprobante asociado, usa la moneda del paquete de la reserva.
        Si no, asume PYG (guaraníes).
        """
        try:
            if obj.comprobante and obj.comprobante.reserva and obj.comprobante.reserva.paquete:
                moneda_obj = obj.comprobante.reserva.paquete.moneda
                if moneda_obj:
                    return moneda_obj.codigo
        except Exception:
            pass
        
        # Por defecto, asumir PYG
        return "PYG"


# ============================================================================
# PAQUETES
# ============================================================================

class PaqueteReporteSerializer(serializers.ModelSerializer):
    """
    Serializer para reporte de paquetes.
    Incluye información de salidas, ocupación y estadísticas.
    """
    # Código del paquete (generar si no existe en modelo)
    codigo = serializers.SerializerMethodField()
    
    # Tipo de paquete
    tipo_paquete = serializers.CharField(source='tipo_paquete.nombre', read_only=True)
    
    # Destino completo
    destino_ciudad = serializers.SerializerMethodField()
    destino_pais = serializers.SerializerMethodField()
    destino_completo = serializers.SerializerMethodField()
    
    # Distribuidora
    distribuidora = serializers.CharField(source='distribuidora.nombre', read_only=True, allow_null=True)
    
    # Información de salidas (próxima salida)
    fecha_inicio = serializers.SerializerMethodField()
    fecha_fin = serializers.SerializerMethodField()
    duracion_dias = serializers.SerializerMethodField()
    
    # Precio y moneda
    precio = serializers.SerializerMethodField()
    precio_unitario = serializers.SerializerMethodField()
    sena = serializers.SerializerMethodField()
    moneda = serializers.SerializerMethodField()
    
    # Precios en dual-moneda
    precio_gs = serializers.SerializerMethodField()
    precio_usd = serializers.SerializerMethodField()
    sena_gs = serializers.SerializerMethodField()
    sena_usd = serializers.SerializerMethodField()
    
    # Cupos (de la próxima salida)
    cantidad_pasajeros = serializers.SerializerMethodField()
    cupos_disponibles = serializers.SerializerMethodField()
    cupos_ocupados = serializers.SerializerMethodField()
    
    # Servicios incluidos
    servicios = serializers.SerializerMethodField()
    
    # Estadísticas
    reservas_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Paquete
        fields = [
            'id',
            'codigo',
            'nombre',
            'tipo_paquete',
            'destino_ciudad',
            'destino_pais',
            'destino_completo',
            'distribuidora',
            'precio',
            'precio_unitario',
            'sena',
            'moneda',
            'precio_gs',
            'precio_usd',
            'sena_gs',
            'sena_usd',
            'fecha_inicio',
            'fecha_fin',
            'duracion_dias',
            'cantidad_pasajeros',
            'cupos_disponibles',
            'cupos_ocupados',
            'personalizado',
            'propio',
            'activo',
            'servicios',
            'reservas_count',
            'fecha_creacion',
        ]
    
    def get_codigo(self, obj):
        """Generar código del paquete si no existe"""
        if hasattr(obj, 'codigo') and obj.codigo:
            return obj.codigo
        return f"PAQ-2024-{obj.id:04d}"
    
    def get_destino_ciudad(self, obj):
        if obj.destino and obj.destino.ciudad:
            return obj.destino.ciudad.nombre
        return "N/A"
    
    def get_destino_pais(self, obj):
        if obj.destino and obj.destino.ciudad and obj.destino.ciudad.pais:
            return obj.destino.ciudad.pais.nombre
        return "N/A"
    
    def get_destino_completo(self, obj):
        ciudad = self.get_destino_ciudad(obj)
        pais = self.get_destino_pais(obj)
        return f"{ciudad}, {pais}"
    
    def get_fecha_inicio(self, obj):
        """Fecha de inicio de la próxima salida"""
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida:
            return proxima_salida.fecha_salida
        return None
    
    def get_fecha_fin(self, obj):
        """Fecha de fin de la próxima salida"""
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida:
            return proxima_salida.fecha_regreso
        return None
    
    def get_duracion_dias(self, obj):
        """Duración en días"""
        inicio = self.get_fecha_inicio(obj)
        fin = self.get_fecha_fin(obj)
        if inicio and fin:
            return (fin - inicio).days + 1
        return None
    
    def get_precio(self, obj):
        """Precio de la próxima salida"""
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida:
            return str(proxima_salida.precio_final or proxima_salida.precio_actual)
        return "0.00"
    
    def get_precio_unitario(self, obj):
        return self.get_precio(obj)
    
    def get_sena(self, obj):
        """Seña de la próxima salida"""
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida and proxima_salida.senia:
            return str(proxima_salida.senia)
        return "0.00"
    
    def get_moneda(self, obj):
        """Moneda del paquete"""
        if obj.moneda:
            return obj.moneda.codigo
        return "PYG"
    
    def get_cantidad_pasajeros(self, obj):
        """
        Cupo total de la próxima salida.
        Si el paquete NO es propio (es de distribuidora), retorna None 
        ya que no manejamos esa información (sujeto a disponibilidad externa).
        """
        # Si es de distribuidora, no manejamos cupos
        if not obj.propio:
            return None
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida:
            return proxima_salida.cupo or 0
        return 0
    
    def get_cupos_ocupados(self, obj):
        """
        Cupos ocupados en la próxima salida.
        Si el paquete NO es propio (es de distribuidora), retorna None 
        ya que no manejamos esa información (sujeto a disponibilidad externa).
        """
        # Si es de distribuidora, no manejamos cupos
        if not obj.propio:
            return None
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if proxima_salida:
            from apps.reserva.models import Reserva
            reservas = Reserva.objects.filter(
                salida=proxima_salida,
                activo=True
            ).exclude(estado='cancelada')
            return sum(r.cantidad_pasajeros or 0 for r in reservas)
        return 0
    
    def get_cupos_disponibles(self, obj):
        """
        Cupos disponibles = total - ocupados.
        Si el paquete NO es propio (es de distribuidora), retorna None 
        ya que no manejamos esa información (sujeto a disponibilidad externa).
        """
        # Si es de distribuidora, no manejamos cupos
        if not obj.propio:
            return None
        
        total = self.get_cantidad_pasajeros(obj)
        ocupados = self.get_cupos_ocupados(obj)
        
        if total is None or ocupados is None:
            return None
        
        return total - ocupados
    
    def get_servicios(self, obj):
        """Lista de servicios incluidos"""
        servicios = obj.paquete_servicios.select_related('servicio').all()
        if servicios.exists():
            return ", ".join([ps.servicio.nombre for ps in servicios if ps.servicio])
        return "No especificado"
    
    def get_reservas_count(self, obj):
        """Cantidad total de reservas del paquete"""
        return obj.reservas.filter(activo=True).exclude(estado='cancelada').count()
    
    def get_precio_gs(self, obj):
        """Precio en guaraníes"""
        from apps.moneda.models import CotizacionMoneda
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if not proxima_salida:
            return None
        
        precio = proxima_salida.precio_final or proxima_salida.precio_actual
        
        # Si el paquete está en Gs, retornar directamente
        if obj.moneda and obj.moneda.codigo == 'PYG':
            return float(precio)
        
        # Si está en otra moneda, convertir a Gs
        if obj.moneda:
            try:
                monto_gs = CotizacionMoneda.convertir_a_guaranies(precio, obj.moneda)
                return float(monto_gs)
            except Exception:
                return None
        
        return float(precio)
    
    def get_precio_usd(self, obj):
        """Precio en dólares"""
        from apps.moneda.models import Moneda, CotizacionMoneda
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if not proxima_salida:
            return None
        
        precio = proxima_salida.precio_final or proxima_salida.precio_actual
        
        # Si el paquete está en USD, retornar directamente
        if obj.moneda and obj.moneda.codigo == 'USD':
            return float(precio)
        
        # Si está en Gs, convertir a USD
        if obj.moneda and obj.moneda.codigo == 'PYG':
            try:
                moneda_usd = Moneda.objects.get(codigo='USD')
                cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                
                if cotizacion and cotizacion.valor_en_guaranies > 0:
                    precio_usd = Decimal(str(precio)) / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(precio_usd, 2))
            except Exception:
                return None
        
        return None
    
    def get_sena_gs(self, obj):
        """Seña en guaraníes"""
        from apps.moneda.models import CotizacionMoneda
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if not proxima_salida or not proxima_salida.senia:
            return None
        
        sena = proxima_salida.senia
        
        # Si el paquete está en Gs, retornar directamente
        if obj.moneda and obj.moneda.codigo == 'PYG':
            return float(sena)
        
        # Si está en otra moneda, convertir a Gs
        if obj.moneda:
            try:
                monto_gs = CotizacionMoneda.convertir_a_guaranies(sena, obj.moneda)
                return float(monto_gs)
            except Exception:
                return None
        
        return float(sena)
    
    def get_sena_usd(self, obj):
        """Seña en dólares"""
        from apps.moneda.models import Moneda, CotizacionMoneda
        
        proxima_salida = obj.salidas.filter(activo=True).order_by('fecha_salida').first()
        if not proxima_salida or not proxima_salida.senia:
            return None
        
        sena = proxima_salida.senia
        
        # Si el paquete está en USD, retornar directamente
        if obj.moneda and obj.moneda.codigo == 'USD':
            return float(sena)
        
        # Si está en Gs, convertir a USD
        if obj.moneda and obj.moneda.codigo == 'PYG':
            try:
                moneda_usd = Moneda.objects.get(codigo='USD')
                cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                
                if cotizacion and cotizacion.valor_en_guaranies > 0:
                    sena_usd = Decimal(str(sena)) / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(sena_usd, 2))
            except Exception:
                return None
        
        return None


# ============================================================================
# RESERVAS
# ============================================================================

class ReservaReporteSerializer(serializers.ModelSerializer):
    """
    Serializer para reporte de reservas.
    Incluye información completa de titular, paquete, pagos y estado.
    """
    # Número de reserva (ID numérico)
    numero = serializers.IntegerField(source='id', read_only=True)
    
    # Información del titular
    titular_nombre = serializers.SerializerMethodField()
    titular_documento = serializers.SerializerMethodField()
    titular_email = serializers.SerializerMethodField()
    titular_telefono = serializers.SerializerMethodField()
    
    # Información del paquete
    paquete_nombre = serializers.CharField(source='paquete.nombre', read_only=True)
    paquete_codigo = serializers.SerializerMethodField()
    
    # Destino
    destino_completo = serializers.SerializerMethodField()
    
    # Fechas de salida
    fecha_salida = serializers.DateField(source='salida.fecha_salida', read_only=True, allow_null=True)
    fecha_retorno = serializers.DateField(source='salida.fecha_regreso', read_only=True, allow_null=True)
    
    # Pasajeros
    pasajeros_asignados = serializers.SerializerMethodField()
    
    # Montos
    monto_total = serializers.SerializerMethodField()
    monto_pagado = serializers.SerializerMethodField()
    saldo_pendiente = serializers.SerializerMethodField()
    porcentaje_pagado = serializers.SerializerMethodField()
    
    # Montos en dual-moneda
    precio_unitario_gs = serializers.SerializerMethodField()
    precio_unitario_usd = serializers.SerializerMethodField()
    monto_total_gs = serializers.SerializerMethodField()
    monto_total_usd = serializers.SerializerMethodField()
    monto_pagado_gs = serializers.SerializerMethodField()
    monto_pagado_usd = serializers.SerializerMethodField()
    saldo_pendiente_gs = serializers.SerializerMethodField()
    saldo_pendiente_usd = serializers.SerializerMethodField()
    
    # Estados
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    estado_pago = serializers.SerializerMethodField()
    estado_pago_display = serializers.SerializerMethodField()
    
    # Modalidad
    modalidad_facturacion_display = serializers.CharField(
        source='get_modalidad_facturacion_display', 
        read_only=True
    )
    
    # Habitación y hotel
    habitacion_tipo = serializers.SerializerMethodField()
    habitacion_numero = serializers.SerializerMethodField()
    hotel_nombre = serializers.SerializerMethodField()
    
    # Condición de pago
    condicion_pago_display = serializers.CharField(
        source='get_condicion_pago_display',
        read_only=True
    )
    
    # Moneda
    moneda = serializers.SerializerMethodField()
    
    class Meta:
        model = Reserva
        fields = [
            'id',
            'numero',
            'codigo',
            'fecha_reserva',
            'titular_nombre',
            'titular_documento',
            'titular_email',
            'titular_telefono',
            'paquete_nombre',
            'paquete_codigo',
            'destino_completo',
            'fecha_salida',
            'fecha_retorno',
            'cantidad_pasajeros',
            'pasajeros_asignados',
            'precio_unitario',
            'precio_unitario_gs',
            'precio_unitario_usd',
            'monto_total',
            'monto_total_gs',
            'monto_total_usd',
            'monto_pagado',
            'monto_pagado_gs',
            'monto_pagado_usd',
            'saldo_pendiente',
            'saldo_pendiente_gs',
            'saldo_pendiente_usd',
            'porcentaje_pagado',
            'estado',
            'estado_display',
            'estado_pago',
            'estado_pago_display',
            'modalidad_facturacion',
            'modalidad_facturacion_display',
            'habitacion_tipo',
            'habitacion_numero',
            'hotel_nombre',
            'condicion_pago',
            'condicion_pago_display',
            'moneda',
            'fecha_modificacion',
        ]
    
    def get_titular_nombre(self, obj):
        if obj.titular:
            # Usar __str__() del modelo que concatena nombre y apellido
            return str(obj.titular)
        return "N/A"
    
    def get_titular_documento(self, obj):
        if obj.titular:
            return obj.titular.documento
        return "N/A"
    
    def get_titular_email(self, obj):
        if obj.titular:
            return obj.titular.email or "N/A"
        return "N/A"
    
    def get_titular_telefono(self, obj):
        if obj.titular:
            return obj.titular.telefono or "N/A"
        return "N/A"
    
    def get_paquete_codigo(self, obj):
        if obj.paquete:
            if hasattr(obj.paquete, 'codigo') and obj.paquete.codigo:
                return obj.paquete.codigo
            return f"PAQ-2024-{obj.paquete.id:04d}"
        return "N/A"
    
    def get_destino_completo(self, obj):
        if obj.paquete and obj.paquete.destino and obj.paquete.destino.ciudad:
            ciudad = obj.paquete.destino.ciudad.nombre
            pais = obj.paquete.destino.ciudad.pais.nombre if obj.paquete.destino.ciudad.pais else ""
            return f"{ciudad}, {pais}"
        return "N/A"
    
    def get_pasajeros_asignados(self, obj):
        """Cantidad de pasajeros ya asignados"""
        return obj.pasajeros.count()
    
    def get_monto_total(self, obj):
        """Monto total = precio_unitario * cantidad_pasajeros"""
        if obj.precio_unitario and obj.cantidad_pasajeros:
            return str(obj.precio_unitario * obj.cantidad_pasajeros)
        return "0.00"
    
    def get_monto_pagado(self, obj):
        """Obtener monto pagado de la property"""
        return str(obj.monto_pagado)
    
    def get_saldo_pendiente(self, obj):
        """Saldo pendiente = monto_total - monto_pagado"""
        monto_total = Decimal(self.get_monto_total(obj))
        monto_pagado = obj.monto_pagado or Decimal('0')
        return str(monto_total - monto_pagado)
    
    def get_porcentaje_pagado(self, obj):
        """Porcentaje pagado"""
        monto_total = Decimal(self.get_monto_total(obj))
        if monto_total > 0:
            monto_pagado = obj.monto_pagado or Decimal('0')
            return round((monto_pagado / monto_total) * 100, 2)
        return 0
    
    def get_estado_pago(self, obj):
        """Calcular estado de pago"""
        monto_pagado = obj.monto_pagado or Decimal('0')
        monto_total = Decimal(self.get_monto_total(obj))
        
        if monto_pagado == 0:
            return "sin_pagar"
        elif monto_pagado < monto_total:
            return "pago_parcial"
        else:
            return "pago_completo"
    
    def get_estado_pago_display(self, obj):
        """Texto legible del estado de pago"""
        estado = self.get_estado_pago(obj)
        estados = {
            'sin_pagar': 'Sin Pagar',
            'pago_parcial': 'Pago Parcial',
            'pago_completo': 'Pago Completo'
        }
        return estados.get(estado, 'N/A')
    
    def get_habitacion_tipo(self, obj):
        if obj.habitacion:
            return obj.habitacion.tipo_habitacion.nombre if obj.habitacion.tipo_habitacion else "N/A"
        return "N/A"
    
    def get_habitacion_numero(self, obj):
        if obj.habitacion:
            return obj.habitacion.numero or "N/A"
        return "N/A"
    
    def get_hotel_nombre(self, obj):
        if obj.habitacion and obj.habitacion.hotel:
            return obj.habitacion.hotel.nombre
        return "N/A"
    
    def get_moneda(self, obj):
        if obj.paquete and obj.paquete.moneda:
            return obj.paquete.moneda.codigo
        return "PYG"
    
    def get_precio_unitario_gs(self, obj):
        """Precio unitario en guaraníes"""
        from apps.moneda.models import CotizacionMoneda
        
        if not obj.precio_unitario:
            return None
        
        # Si el paquete está en Gs, retornar directamente
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'PYG':
            return float(obj.precio_unitario)
        
        # Si está en otra moneda, convertir a Gs
        if obj.paquete and obj.paquete.moneda:
            try:
                monto_gs = CotizacionMoneda.convertir_a_guaranies(obj.precio_unitario, obj.paquete.moneda)
                return float(monto_gs)
            except Exception:
                return None
        
        return float(obj.precio_unitario)
    
    def get_precio_unitario_usd(self, obj):
        """Precio unitario en dólares"""
        from apps.moneda.models import Moneda, CotizacionMoneda
        
        if not obj.precio_unitario:
            return None
        
        # Si el paquete está en USD, retornar directamente
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'USD':
            return float(obj.precio_unitario)
        
        # Si está en Gs, convertir a USD
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'PYG':
            try:
                moneda_usd = Moneda.objects.get(codigo='USD')
                cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                
                if cotizacion and cotizacion.valor_en_guaranies > 0:
                    precio_usd = Decimal(str(obj.precio_unitario)) / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(precio_usd, 2))
            except Exception:
                return None
        
        return None
    
    def get_monto_total_gs(self, obj):
        """Monto total en guaraníes"""
        precio_gs = self.get_precio_unitario_gs(obj)
        if precio_gs is not None and obj.cantidad_pasajeros:
            return float(precio_gs * obj.cantidad_pasajeros)
        return None
    
    def get_monto_total_usd(self, obj):
        """Monto total en dólares"""
        precio_usd = self.get_precio_unitario_usd(obj)
        if precio_usd is not None and obj.cantidad_pasajeros:
            return float(round(precio_usd * obj.cantidad_pasajeros, 2))
        return None
    
    def get_monto_pagado_gs(self, obj):
        """Monto pagado en guaraníes"""
        from apps.moneda.models import CotizacionMoneda
        
        if not obj.monto_pagado:
            return 0.0
        
        # Si el paquete está en Gs, retornar directamente
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'PYG':
            return float(obj.monto_pagado)
        
        # Si está en otra moneda, convertir a Gs
        if obj.paquete and obj.paquete.moneda:
            try:
                monto_gs = CotizacionMoneda.convertir_a_guaranies(obj.monto_pagado, obj.paquete.moneda)
                return float(monto_gs)
            except Exception:
                return None
        
        return float(obj.monto_pagado)
    
    def get_monto_pagado_usd(self, obj):
        """Monto pagado en dólares"""
        from apps.moneda.models import Moneda, CotizacionMoneda
        
        if not obj.monto_pagado:
            return 0.0
        
        # Si el paquete está en USD, retornar directamente
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'USD':
            return float(obj.monto_pagado)
        
        # Si está en Gs, convertir a USD
        if obj.paquete and obj.paquete.moneda and obj.paquete.moneda.codigo == 'PYG':
            try:
                moneda_usd = Moneda.objects.get(codigo='USD')
                cotizacion = CotizacionMoneda.obtener_cotizacion_vigente(moneda_usd)
                
                if cotizacion and cotizacion.valor_en_guaranies > 0:
                    monto_usd = Decimal(str(obj.monto_pagado)) / Decimal(str(cotizacion.valor_en_guaranies))
                    return float(round(monto_usd, 2))
            except Exception:
                return None
        
        return None
    
    def get_saldo_pendiente_gs(self, obj):
        """Saldo pendiente en guaraníes"""
        monto_total_gs = self.get_monto_total_gs(obj)
        monto_pagado_gs = self.get_monto_pagado_gs(obj)
        
        if monto_total_gs is not None and monto_pagado_gs is not None:
            return float(monto_total_gs - monto_pagado_gs)
        return None
    
    def get_saldo_pendiente_usd(self, obj):
        """Saldo pendiente en dólares"""
        monto_total_usd = self.get_monto_total_usd(obj)
        monto_pagado_usd = self.get_monto_pagado_usd(obj)
        
        if monto_total_usd is not None and monto_pagado_usd is not None:
            return float(round(monto_total_usd - monto_pagado_usd, 2))
        return None

