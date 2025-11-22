"""
Dashboard Views - Versión Completa
Endpoints para reportes y métricas del home
Incluye: ocupación, top destinos, crecimiento, y alertas mejoradas
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import timedelta, datetime, date
from decimal import Decimal
from collections import defaultdict
import calendar

from apps.arqueo_caja.models import Caja, AperturaCaja, MovimientoCaja
from apps.reserva.models import Reserva
from apps.facturacion.models import FacturaElectronica
from apps.paquete.models import Paquete, SalidaPaquete
from apps.destino.models import Destino


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def resumen_general(request):
    """
    GET /api/dashboard/resumen-general/
    
    Retorna métricas generales del negocio (versión simplificada)
    
    Parámetros opcionales:
    - periodo: 'hoy' (default), 'semana', 'mes'
    """
    try:
        periodo = request.query_params.get('periodo', 'hoy')
        
        # Calcular fechas según período
        ahora = timezone.now()
        if periodo == 'hoy':
            fecha_desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        elif periodo == 'semana':
            fecha_desde = ahora - timedelta(days=7)
        elif periodo == 'mes':
            fecha_desde = ahora - timedelta(days=30)
        else:
            fecha_desde = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # ===== MÉTRICAS FINANCIERAS (Cajas) =====
        cajas_abiertas = Caja.objects.filter(estado_actual='abierta', activo=True).count()
        cajas_cerradas = Caja.objects.filter(estado_actual='cerrada', activo=True).count()
        
        # Saldo total de todas las cajas activas
        saldo_total = Caja.objects.filter(activo=True).aggregate(
            total=Sum('saldo_actual')
        )['total'] or Decimal('0')
        
        # Ingresos y egresos del período
        movimientos_periodo = MovimientoCaja.objects.filter(
            fecha_hora_movimiento__gte=fecha_desde,
            apertura_caja__esta_abierta=True
        )
        
        ingresos_periodo = movimientos_periodo.filter(
            tipo_movimiento='ingreso'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        egresos_periodo = movimientos_periodo.filter(
            tipo_movimiento='egreso'
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        balance_periodo = ingresos_periodo - egresos_periodo
        
        # ===== MÉTRICAS DE RESERVAS =====
        reservas_pendientes = Reserva.objects.filter(
            estado='pendiente',
            activo=True
        ).count()
        
        reservas_confirmadas = Reserva.objects.filter(
            estado='confirmada',
            activo=True
        ).count()
        
        reservas_finalizadas_mes = Reserva.objects.filter(
            estado='finalizada',
            activo=True,
            fecha_reserva__gte=ahora - timedelta(days=30)
        ).count()
        
        reservas_canceladas_mes = Reserva.objects.filter(
            estado='cancelada',
            activo=True,
            fecha_reserva__gte=ahora - timedelta(days=30)
        ).count()
        
        # Próximas salidas (reservas con salidas en los próximos 7 días)
        fecha_limite = ahora + timedelta(days=7)
        proximas_salidas = Reserva.objects.filter(
            activo=True,
            salida__fecha_salida__gte=ahora.date(),
            salida__fecha_salida__lte=fecha_limite.date()
        ).exclude(estado='cancelada').count()
        
        # NUEVO: Cálculo de ocupación (%)
        # Obtener todas las salidas futuras activas
        salidas_futuras = SalidaPaquete.objects.filter(
            fecha_salida__gte=ahora.date(),
            activo=True
        )
        
        cupos_totales = 0
        cupos_ocupados = 0
        
        for salida in salidas_futuras:
            # Cupos totales de esta salida (campo 'cupo' singular)
            cupos_salida = salida.cupo or 0
            cupos_totales += cupos_salida
            
            # Cupos ocupados (contar pasajeros de reservas activas no canceladas)
            reservas_salida = Reserva.objects.filter(
                salida=salida,
                activo=True
            ).exclude(estado='cancelada')
            
            for reserva in reservas_salida:
                cupos_ocupados += reserva.cantidad_pasajeros or 0
        
        # Calcular porcentaje de ocupación
        if cupos_totales > 0:
            ocupacion_porcentaje = round((cupos_ocupados / cupos_totales) * 100, 1)
        else:
            ocupacion_porcentaje = 0
        
        cupos_disponibles = cupos_totales - cupos_ocupados
        
        # ===== MÉTRICAS DE FACTURACIÓN =====
        # Facturas del día
        facturas_hoy = FacturaElectronica.objects.filter(
            fecha_emision__gte=fecha_desde,
            activo=True,
            fecha_anulacion__isnull=True
        ).count()
        
        # Facturas del mes
        inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        facturas_mes = FacturaElectronica.objects.filter(
            fecha_emision__gte=inicio_mes,
            activo=True,
            fecha_anulacion__isnull=True
        ).count()
        
        # Monto facturado del día
        monto_facturado_hoy = FacturaElectronica.objects.filter(
            fecha_emision__gte=fecha_desde,
            activo=True,
            fecha_anulacion__isnull=True
        ).aggregate(total=Sum('total_general'))['total'] or Decimal('0')
        
        # Monto facturado del mes
        monto_facturado_mes = FacturaElectronica.objects.filter(
            fecha_emision__gte=inicio_mes,
            activo=True,
            fecha_anulacion__isnull=True
        ).aggregate(total=Sum('total_general'))['total'] or Decimal('0')
        
        # NUEVO: Saldo por cobrar (facturas a crédito con saldo pendiente)
        # Calculamos: total_general - total_acreditado para facturas a crédito
        facturas_credito = FacturaElectronica.objects.filter(
            activo=True,
            fecha_anulacion__isnull=True,
            condicion_venta='credito'
        )
        
        saldo_por_cobrar = Decimal('0')
        for factura in facturas_credito:
            saldo_pendiente = factura.total_general - (factura.total_acreditado or Decimal('0'))
            if saldo_pendiente > 0:
                saldo_por_cobrar += saldo_pendiente
        
        # NUEVO: Comparación con mes anterior (crecimiento %)
        # Calcular inicio y fin del mes anterior
        primer_dia_mes_actual = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ultimo_dia_mes_anterior = primer_dia_mes_actual - timedelta(days=1)
        primer_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monto_mes_anterior = FacturaElectronica.objects.filter(
            fecha_emision__gte=primer_dia_mes_anterior,
            fecha_emision__lt=primer_dia_mes_actual,
            activo=True,
            fecha_anulacion__isnull=True
        ).aggregate(total=Sum('total_general'))['total'] or Decimal('0')
        
        # Calcular crecimiento %
        if monto_mes_anterior > 0:
            diferencia = monto_facturado_mes - monto_mes_anterior
            porcentaje_crecimiento = round((diferencia / monto_mes_anterior) * 100, 1)
            if porcentaje_crecimiento > 0:
                tendencia = "positiva"
            elif porcentaje_crecimiento < 0:
                tendencia = "negativa"
            else:
                tendencia = "estable"
        else:
            diferencia = monto_facturado_mes
            porcentaje_crecimiento = 100 if monto_facturado_mes > 0 else 0
            tendencia = "nueva"
        
        # Construir respuesta
        data = {
            "success": True,
            "periodo": periodo,
            "fecha_actualizacion": ahora.isoformat(),
            "data": {
                "financiero": {
                    "cajas_abiertas": cajas_abiertas,
                    "cajas_cerradas": cajas_cerradas,
                    "saldo_total_cajas": str(saldo_total),
                    "ingresos_periodo": str(ingresos_periodo),
                    "egresos_periodo": str(egresos_periodo),
                    "balance_periodo": str(balance_periodo),
                    "moneda": "PYG"
                },
                "reservas": {
                    "pendientes": reservas_pendientes,
                    "confirmadas": reservas_confirmadas,
                    "finalizadas_mes": reservas_finalizadas_mes,
                    "canceladas_mes": reservas_canceladas_mes,
                    "proximas_salidas_7d": proximas_salidas,
                    "ocupacion_porcentaje": ocupacion_porcentaje,
                    "cupos_totales": cupos_totales,
                    "cupos_ocupados": cupos_ocupados,
                    "cupos_disponibles": cupos_disponibles
                },
                "facturacion": {
                    "facturas_emitidas_hoy": facturas_hoy,
                    "facturas_emitidas_mes": facturas_mes,
                    "monto_total_hoy": str(monto_facturado_hoy),
                    "monto_total_mes": str(monto_facturado_mes),
                    "saldo_por_cobrar": str(saldo_por_cobrar),
                    "comparacion_mes_anterior": {
                        "monto_mes_anterior": str(monto_mes_anterior),
                        "diferencia": str(diferencia),
                        "porcentaje_crecimiento": porcentaje_crecimiento,
                        "tendencia": tendencia
                    }
                }
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al obtener resumen general",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def alertas(request):
    """
    GET /api/dashboard/alertas/
    
    Retorna alertas críticas y advertencias (versión simplificada)
    
    Parámetros opcionales:
    - tipo: 'criticas', 'advertencias', 'todas' (default: 'todas')
    """
    try:
        tipo_filtro = request.query_params.get('tipo', 'todas')
        ahora = timezone.now()
        
        alertas_criticas = []
        alertas_advertencias = []
        
        # ===== ALERTA CRÍTICA 1: Cajas abiertas más de 12 horas =====
        if tipo_filtro in ['criticas', 'todas']:
            limite_horas = ahora - timedelta(hours=12)
            aperturas_antiguas = AperturaCaja.objects.filter(
                esta_abierta=True,
                fecha_hora_apertura__lt=limite_horas
            ).select_related('caja', 'responsable')
            
            for apertura in aperturas_antiguas:
                horas_abierta = (ahora - apertura.fecha_hora_apertura).total_seconds() / 3600
                alertas_criticas.append({
                    "id": f"caja_abierta_{apertura.id}",
                    "tipo": "caja_abierta_tiempo_excedido",
                    "severidad": "alta",
                    "titulo": "Caja abierta más de 12 horas",
                    "mensaje": f"La {apertura.caja.nombre} lleva {int(horas_abierta)} horas abierta sin cierre",
                    "accion_url": "/arqueo-caja/cajas",
                    "accion_texto": "Cerrar caja",
                    "fecha_creacion": apertura.fecha_hora_apertura.isoformat(),
                    "metadata": {
                        "caja_id": apertura.caja.id,
                        "caja_nombre": apertura.caja.nombre,
                        "horas_abierta": int(horas_abierta)
                    }
                })
        
        # ===== ALERTA CRÍTICA 2: Reservas con pagos pendientes próximas a vencer =====
        if tipo_filtro in ['criticas', 'todas']:
            # Reservas que tienen salida en menos de 7 días y no están finalizadas
            fecha_limite = ahora + timedelta(days=7)
            reservas_riesgo = Reserva.objects.filter(
                activo=True,
                estado__in=['pendiente', 'confirmada'],  # No finalizadas
                salida__fecha_salida__gte=ahora,
                salida__fecha_salida__lte=fecha_limite
            ).select_related('salida')
            
            for reserva in reservas_riesgo:
                dias_hasta_salida = (reserva.salida.fecha_salida - ahora.date()).days
                alertas_criticas.append({
                    "id": f"reserva_pago_{reserva.id}",
                    "tipo": "reserva_pago_pendiente",
                    "severidad": "alta",
                    "titulo": "Reserva con pago pendiente próxima a salida",
                    "mensaje": f"Reserva {reserva.codigo} tiene salida en {dias_hasta_salida} días y pago pendiente",
                    "accion_url": f"/paquetes_viajes/reservas?id={reserva.id}",
                    "accion_texto": "Ver reserva",
                    "fecha_creacion": reserva.fecha_reserva.isoformat(),
                    "metadata": {
                        "reserva_id": reserva.id,
                        "reserva_codigo": reserva.codigo,
                        "dias_hasta_salida": dias_hasta_salida,
                        "estado": reserva.estado
                    }
                })
        
        # ===== ADVERTENCIA 1: Reservas confirmadas sin pasajeros asignados =====
        if tipo_filtro in ['advertencias', 'todas']:
            reservas_sin_pasajeros = Reserva.objects.filter(
                activo=True,
                estado='confirmada'
            ).annotate(
                cant_pasajeros=Count('pasajeros')
            ).filter(cant_pasajeros=0)
            
            if reservas_sin_pasajeros.exists():
                cantidad = reservas_sin_pasajeros.count()
                ids_reservas = list(reservas_sin_pasajeros.values_list('id', flat=True))
                
                alertas_advertencias.append({
                    "id": "reservas_sin_pasajeros",
                    "tipo": "reserva_sin_pasajeros",
                    "severidad": "media",
                    "titulo": "Reservas sin asignar pasajeros",
                    "mensaje": f"{cantidad} reservas confirmadas sin pasajeros asignados",
                    "accion_url": "/paquetes_viajes/reservas?filtro=sin_pasajeros",
                    "accion_texto": "Asignar pasajeros",
                    "fecha_creacion": ahora.isoformat(),
                    "metadata": {
                        "cantidad": cantidad,
                        "reservas_ids": ids_reservas
                    }
                })
        
        # ===== ADVERTENCIA 2: Paquetes próximos con cupos disponibles =====
        if tipo_filtro in ['advertencias', 'todas']:
            fecha_limite_salida = ahora.date() + timedelta(days=7)
            
            salidas_proximas = SalidaPaquete.objects.filter(
                fecha_salida__gte=ahora.date(),
                fecha_salida__lte=fecha_limite_salida,
                activo=True
            ).select_related('paquete')
            
            paquetes_con_cupos = []
            for salida in salidas_proximas:
                # Contar cupos ocupados
                reservas_salida = Reserva.objects.filter(
                    salida=salida,
                    activo=True
                ).exclude(estado='cancelada')
                
                cupos_ocupados_salida = sum(
                    r.cantidad_pasajeros or 0 for r in reservas_salida
                )
                cupos_disponibles_salida = (salida.cupo or 0) - cupos_ocupados_salida
                
                if cupos_disponibles_salida > 0:
                    dias_hasta_salida = (salida.fecha_salida - ahora.date()).days
                    paquetes_con_cupos.append({
                        "id": salida.paquete.id,
                        "nombre": salida.paquete.nombre,
                        "cupos_disponibles": cupos_disponibles_salida,
                        "dias_hasta_salida": dias_hasta_salida,
                        "fecha_salida": salida.fecha_salida.isoformat()
                    })
            
            if paquetes_con_cupos:
                alertas_advertencias.append({
                    "id": "paquetes_cupos_disponibles",
                    "tipo": "paquete_cupos_disponibles",
                    "severidad": "media",
                    "titulo": "Paquetes próximos con cupos disponibles",
                    "mensaje": f"{len(paquetes_con_cupos)} paquetes con salida en 7 días tienen cupos sin vender",
                    "accion_url": "/paquetes_viajes/paquetes?filtro=proximos_cupos",
                    "accion_texto": "Ver paquetes",
                    "fecha_creacion": ahora.isoformat(),
                    "metadata": {
                        "cantidad": len(paquetes_con_cupos),
                        "paquetes": paquetes_con_cupos[:5]  # Solo primeros 5
                    }
                })
        
        # Construir respuesta
        total_alertas = len(alertas_criticas) + len(alertas_advertencias)
        
        data = {
            "success": True,
            "fecha_actualizacion": ahora.isoformat(),
            "total_alertas": total_alertas,
            "data": {
                "criticas": alertas_criticas,
                "advertencias": alertas_advertencias,
                "informativas": []
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al obtener alertas",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def metricas_ventas(request):
    """
    GET /api/dashboard/metricas-ventas/
    
    Retorna datos históricos de ventas para gráficos (versión simplificada)
    
    Parámetros opcionales:
    - periodo: '7d', '30d' (default: '30d')
    """
    try:
        periodo = request.query_params.get('periodo', '30d')
        
        # Calcular fecha desde
        ahora = timezone.now()
        if periodo == '7d':
            fecha_desde = ahora - timedelta(days=7)
        elif periodo == '30d':
            fecha_desde = ahora - timedelta(days=30)
        else:
            fecha_desde = ahora - timedelta(days=30)
        
        # Obtener reservas del período agrupadas por día
        from django.db.models.functions import TruncDate
        from collections import defaultdict
        
        # Obtener todas las reservas del período
        reservas = Reserva.objects.filter(
            fecha_reserva__gte=fecha_desde,
            activo=True
        ).exclude(
            estado='cancelada'
        ).select_related('salida')
        
        # Agrupar por fecha manualmente (porque monto_total es property)
        ventas_por_fecha = defaultdict(lambda: {'cantidad': 0, 'monto': Decimal('0')})
        
        for reserva in reservas:
            fecha_str = reserva.fecha_reserva.date().isoformat()
            ventas_por_fecha[fecha_str]['cantidad'] += 1
            # Calcular monto: precio_unitario * cantidad_pasajeros
            if reserva.precio_unitario and reserva.cantidad_pasajeros:
                monto_reserva = reserva.precio_unitario * reserva.cantidad_pasajeros
                ventas_por_fecha[fecha_str]['monto'] += monto_reserva
        
        # Formatear datos
        ventas_diarias = []
        for fecha_str in sorted(ventas_por_fecha.keys()):
            datos = ventas_por_fecha[fecha_str]
            ventas_diarias.append({
                "fecha": fecha_str,
                "cantidad_reservas": datos['cantidad'],
                "monto_total": str(datos['monto'])
            })
        
        # Resumen del período
        total_reservas = sum(v['cantidad_reservas'] for v in ventas_diarias)
        monto_total = sum(Decimal(v['monto_total']) for v in ventas_diarias)
        
        data = {
            "success": True,
            "periodo": periodo,
            "fecha_desde": fecha_desde.date().isoformat(),
            "fecha_hasta": ahora.date().isoformat(),
            "data": {
                "ventas_diarias": ventas_diarias,
                "resumen_periodo": {
                    "total_reservas": total_reservas,
                    "monto_total": str(monto_total)
                }
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al obtener métricas de ventas",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_destinos(request):
    """
    GET /api/dashboard/top-destinos/
    
    Retorna los destinos más vendidos del período
    
    Parámetros opcionales:
    - periodo: 'mes' (default), 'trimestre', 'año'
    - limite: cantidad de resultados (default: 5)
    """
    try:
        periodo = request.query_params.get('periodo', 'mes')
        limite = int(request.query_params.get('limite', 5))
        
        # Calcular fecha desde
        ahora = timezone.now()
        if periodo == 'mes':
            fecha_desde = ahora - timedelta(days=30)
        elif periodo == 'trimestre':
            fecha_desde = ahora - timedelta(days=90)
        elif periodo == 'año':
            fecha_desde = ahora - timedelta(days=365)
        else:
            fecha_desde = ahora - timedelta(days=30)
        
        # Obtener paquetes con destino
        from collections import defaultdict
        
        destinos_stats = defaultdict(lambda: {
            'cantidad_reservas': 0,
            'monto_total': Decimal('0'),
            'paquetes_activos': set()
        })
        
        # Obtener todas las reservas del período con sus paquetes y destinos
        reservas = Reserva.objects.filter(
            fecha_reserva__gte=fecha_desde,
            activo=True
        ).exclude(
            estado='cancelada'
        ).select_related('paquete')
        
        for reserva in reservas:
            if reserva.paquete and reserva.paquete.destino and reserva.paquete.destino.ciudad:
                destino = reserva.paquete.destino
                ciudad_nombre = destino.ciudad.nombre
                pais_nombre = destino.ciudad.pais.nombre if destino.ciudad.pais else "Sin país"
                destino_key = f"{ciudad_nombre}, {pais_nombre}"
                
                # Calcular monto de la reserva
                monto_reserva = Decimal('0')
                if reserva.precio_unitario and reserva.cantidad_pasajeros:
                    monto_reserva = reserva.precio_unitario * reserva.cantidad_pasajeros
                
                destinos_stats[destino_key]['cantidad_reservas'] += 1
                destinos_stats[destino_key]['monto_total'] += monto_reserva
                destinos_stats[destino_key]['paquetes_activos'].add(reserva.paquete.id)
                destinos_stats[destino_key]['destino_id'] = destino.id
                destinos_stats[destino_key]['ciudad'] = ciudad_nombre
                destinos_stats[destino_key]['pais'] = pais_nombre
        
        # Convertir a lista y ordenar por cantidad de reservas
        top_destinos_list = []
        for destino_nombre, stats in destinos_stats.items():
            top_destinos_list.append({
                "destino_id": stats.get('destino_id'),
                "ciudad": stats.get('ciudad', ''),
                "pais": stats.get('pais', ''),
                "destino_completo": destino_nombre,
                "cantidad_reservas": stats['cantidad_reservas'],
                "monto_total": str(stats['monto_total']),
                "paquetes_activos": len(stats['paquetes_activos'])
            })
        
        # Ordenar por cantidad de reservas descendente
        top_destinos_list.sort(key=lambda x: x['cantidad_reservas'], reverse=True)
        
        # Limitar resultados
        top_destinos_list = top_destinos_list[:limite]
        
        data = {
            "success": True,
            "periodo": periodo,
            "fecha_desde": fecha_desde.date().isoformat(),
            "fecha_hasta": ahora.date().isoformat(),
            "data": {
                "top_destinos": top_destinos_list
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                "success": False,
                "message": "Error al obtener top destinos",
                "errors": [str(e)]
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

