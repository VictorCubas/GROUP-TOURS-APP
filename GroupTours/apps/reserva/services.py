"""
Servicios de negocio para la app de reservas.
Contiene funciones reutilizables para obtener y procesar información de reservas.
"""
from django.core.exceptions import ObjectDoesNotExist
from .models import Reserva


def obtener_detalle_reserva(reserva_id):
    """
    Obtiene toda la información detallada de una reserva por su ID.

    Este servicio recupera una reserva con todas sus relaciones precargadas
    para minimizar las consultas a la base de datos.

    Args:
        reserva_id (int): ID de la reserva a consultar

    Returns:
        Reserva: Instancia de Reserva con todas las relaciones precargadas

    Raises:
        ObjectDoesNotExist: Si la reserva no existe

    Example:
        >>> reserva = obtener_detalle_reserva(1)
        >>> print(reserva.codigo)
        'RSV-2025-0001'
        >>> print(reserva.paquete.nombre)
        'Tour a Encarnación'
    """
    try:
        reserva = Reserva.objects.select_related(
            # Relaciones directas
            'titular',
            'paquete',
            'salida',
            'habitacion',
            # Relaciones del paquete
            'paquete__tipo_paquete',
            'paquete__destino',
            'paquete__destino__ciudad',
            'paquete__destino__ciudad__pais',
            'paquete__moneda',
            'paquete__distribuidora',
            # Relaciones de la salida
            'salida__temporada',
            # Relaciones de la habitación
            'habitacion__hotel',
            'habitacion__hotel__cadena',
            'habitacion__hotel__ciudad',
        ).prefetch_related(
            # Pasajeros y sus pagos
            'pasajeros',
            'pasajeros__persona',
            'pasajeros__distribuciones_pago',
            'pasajeros__distribuciones_pago__comprobante',
            # Servicios adicionales
            'servicios_adicionales',
            'servicios_adicionales__servicio',
            # Comprobantes de pago
            'comprobantes',
            'comprobantes__distribuciones',
            'comprobantes__distribuciones__pasajero',
            'comprobantes__distribuciones__pasajero__persona',
            'comprobantes__empleado',
            'comprobantes__empleado__persona',
            # Servicios base del paquete
            'paquete__paquete_servicios',
            'paquete__paquete_servicios__servicio',
        ).get(id=reserva_id)

        return reserva

    except Reserva.DoesNotExist:
        raise ObjectDoesNotExist(f"No existe una reserva con ID {reserva_id}")


def obtener_resumen_reserva(reserva_id):
    """
    Obtiene un resumen simplificado de la reserva con datos clave.

    Args:
        reserva_id (int): ID de la reserva

    Returns:
        dict: Diccionario con información resumida de la reserva

    Raises:
        ObjectDoesNotExist: Si la reserva no existe

    Example:
        >>> resumen = obtener_resumen_reserva(1)
        >>> print(resumen['codigo'])
        'RSV-2025-0001'
        >>> print(resumen['estado'])
        'confirmada'
    """
    reserva = obtener_detalle_reserva(reserva_id)

    # Construir información del destino de forma segura
    destino_info = None
    if reserva.paquete and reserva.paquete.destino:
        destino_info = {
            'ciudad': None,
            'pais': None,
        }
        if hasattr(reserva.paquete.destino, 'ciudad') and reserva.paquete.destino.ciudad:
            destino_info['ciudad'] = reserva.paquete.destino.ciudad.nombre
            if hasattr(reserva.paquete.destino.ciudad, 'pais') and reserva.paquete.destino.ciudad.pais:
                destino_info['pais'] = reserva.paquete.destino.ciudad.pais.nombre

    return {
        'id': reserva.id,
        'codigo': reserva.codigo,
        'estado': reserva.estado,
        'estado_display': reserva.estado_display,
        'fecha_reserva': reserva.fecha_reserva,
        'titular': {
            'id': reserva.titular.id,
            'nombre_completo': f"{reserva.titular.nombre} {reserva.titular.apellido}",
            'documento': reserva.titular.documento,
            'email': reserva.titular.email,
            'telefono': reserva.titular.telefono,
        } if reserva.titular else None,
        'paquete': {
            'id': reserva.paquete.id,
            'nombre': reserva.paquete.nombre,
            'destino': destino_info,
        } if reserva.paquete else None,
        'fechas': {
            'salida': reserva.salida.fecha_salida if reserva.salida else None,
            'regreso': reserva.salida.fecha_regreso if reserva.salida else None,
        },
        'cantidad_pasajeros': reserva.cantidad_pasajeros,
        'costos': {
            'precio_unitario': float(reserva.precio_base_paquete),
            'costo_total': float(reserva.costo_total_estimado),
            'monto_pagado': float(reserva.monto_pagado),
            'saldo_pendiente': float(reserva.costo_total_estimado - reserva.monto_pagado),
            'seña_total': float(reserva.seña_total),
            'moneda': {
                'simbolo': reserva.paquete.moneda.simbolo,
                'codigo': reserva.paquete.moneda.codigo,
            } if reserva.paquete and reserva.paquete.moneda else None,
        },
        'validaciones': {
            'puede_confirmarse': reserva.puede_confirmarse(),
            'esta_totalmente_pagada': reserva.esta_totalmente_pagada(),
            'datos_completos': reserva.datos_completos,
        }
    }


def obtener_pasajeros_reserva(reserva_id):
    """
    Obtiene la lista de pasajeros de una reserva con su información de pagos.

    Args:
        reserva_id (int): ID de la reserva

    Returns:
        list: Lista de diccionarios con información de cada pasajero

    Raises:
        ObjectDoesNotExist: Si la reserva no existe

    Example:
        >>> pasajeros = obtener_pasajeros_reserva(1)
        >>> print(len(pasajeros))
        2
        >>> print(pasajeros[0]['persona']['nombre'])
        'Juan'
    """
    reserva = obtener_detalle_reserva(reserva_id)

    pasajeros = []
    for pasajero in reserva.pasajeros.all():
        pasajeros.append({
            'id': pasajero.id,
            'es_titular': pasajero.es_titular,
            'persona': {
                'id': pasajero.persona.id,
                'nombre': pasajero.persona.nombre,
                'apellido': pasajero.persona.apellido,
                'nombre_completo': f"{pasajero.persona.nombre} {pasajero.persona.apellido}",
                'documento': pasajero.persona.documento,
                'tipo_documento': {
                    'id': pasajero.persona.tipo_documento.id,
                    'nombre': pasajero.persona.tipo_documento.nombre,
                } if pasajero.persona.tipo_documento else None,
                'email': pasajero.persona.email,
                'telefono': pasajero.persona.telefono,
            },
            'precio_asignado': float(pasajero.precio_asignado) if pasajero.precio_asignado else 0,
            'monto_pagado': float(pasajero.monto_pagado),
            'saldo_pendiente': float(pasajero.saldo_pendiente),
            'porcentaje_pagado': float(pasajero.porcentaje_pagado),
            'seña_requerida': float(pasajero.seña_requerida),
            'tiene_sena_pagada': pasajero.tiene_sena_pagada,
            'esta_totalmente_pagado': pasajero.esta_totalmente_pagado,
            'ticket_numero': pasajero.ticket_numero,
            'voucher_codigo': pasajero.voucher_codigo,
        })

    return pasajeros


def obtener_comprobantes_reserva(reserva_id):
    """
    Obtiene los últimos 3 comprobantes de pago de una reserva.

    Args:
        reserva_id (int): ID de la reserva

    Returns:
        list: Lista de diccionarios con información de los últimos 3 comprobantes

    Raises:
        ObjectDoesNotExist: Si la reserva no existe

    Example:
        >>> comprobantes = obtener_comprobantes_reserva(1)
        >>> print(len(comprobantes))
        3
        >>> print(comprobantes[0]['numero_comprobante'])
        'CPG-2025-0001'
    """
    reserva = obtener_detalle_reserva(reserva_id)

    comprobantes = []
    for comp in reserva.comprobantes.filter(activo=True).order_by('-fecha_pago')[:3]:
        distribuciones = []
        for dist in comp.distribuciones.all():
            distribuciones.append({
                'pasajero_id': dist.pasajero.id,
                'pasajero_nombre': f"{dist.pasajero.persona.nombre} {dist.pasajero.persona.apellido}",
                'monto': float(dist.monto),
                'observaciones': dist.observaciones,
            })

        # Obtener nombre del empleado de forma segura
        empleado_data = None
        if comp.empleado:
            persona = comp.empleado.persona
            if hasattr(persona, 'personafisica'):
                pf = persona.personafisica
                empleado_data = {
                    'id': comp.empleado.id,
                    'nombre': f"{pf.nombre} {pf.apellido or ''}".strip(),
                }
            elif hasattr(persona, 'nombre'):
                empleado_data = {
                    'id': comp.empleado.id,
                    'nombre': f"{persona.nombre} {getattr(persona, 'apellido', '') or ''}".strip(),
                }
            else:
                empleado_data = {
                    'id': comp.empleado.id,
                    'nombre': persona.documento,
                }

        comprobantes.append({
            'id': comp.id,
            'numero_comprobante': comp.numero_comprobante,
            'fecha_pago': comp.fecha_pago,
            'fecha_creacion': comp.fecha_creacion,
            'tipo': comp.tipo,
            'tipo_display': comp.get_tipo_display(),
            'metodo_pago': comp.metodo_pago,
            'metodo_pago_display': comp.get_metodo_pago_display(),
            'monto': float(comp.monto),
            'referencia': comp.referencia,
            'observaciones': comp.observaciones,
            'distribuciones': distribuciones,
            'empleado': empleado_data,
            'pdf_url': comp.pdf_generado.url if comp.pdf_generado else None,
        })

    return comprobantes


def obtener_servicios_reserva(reserva_id):
    """
    Obtiene todos los servicios (base y adicionales) de una reserva.

    Args:
        reserva_id (int): ID de la reserva

    Returns:
        dict: Diccionario con 'servicios_base' y 'servicios_adicionales'

    Raises:
        ObjectDoesNotExist: Si la reserva no existe

    Example:
        >>> servicios = obtener_servicios_reserva(1)
        >>> print(len(servicios['servicios_base']))
        5
        >>> print(len(servicios['servicios_adicionales']))
        2
    """
    reserva = obtener_detalle_reserva(reserva_id)

    # Servicios base del paquete
    servicios_base = []
    if reserva.paquete:
        for ps in reserva.paquete.paquete_servicios.all():
            servicios_base.append({
                'id': ps.id,
                'servicio': {
                    'id': ps.servicio.id,
                    'nombre': ps.servicio.nombre,
                    'descripcion': ps.servicio.descripcion,
                    'tipo': ps.servicio.tipo,
                },
                'precio': float(ps.precio) if ps.precio else 0,
            })

    # Servicios adicionales
    servicios_adicionales = []
    for sa in reserva.servicios_adicionales.filter(activo=True):
        servicios_adicionales.append({
            'id': sa.id,
            'servicio': {
                'id': sa.servicio.id,
                'nombre': sa.servicio.nombre,
                'descripcion': sa.servicio.descripcion,
            },
            'cantidad': sa.cantidad,
            'precio_unitario': float(sa.precio_unitario),
            'subtotal': float(sa.subtotal),
            'observacion': sa.observacion,
            'fecha_agregado': sa.fecha_agregado,
        })

    return {
        'servicios_base': servicios_base,
        'servicios_adicionales': servicios_adicionales,
        'costo_servicios_adicionales': float(reserva.costo_servicios_adicionales),
    }
