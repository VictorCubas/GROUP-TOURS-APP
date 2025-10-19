# Comando: analizar_paquete

Este comando de Django permite analizar los precios de un paquete turístico específico y su salida, mostrando qué habitación corresponde al precio mínimo y máximo.

## Uso

```bash
python manage.py analizar_paquete <paquete_id> <salida_id>
```

### Parámetros

- `paquete_id`: ID del paquete turístico a analizar
- `salida_id`: ID de la salida específica del paquete

### Ejemplo

```bash
python manage.py analizar_paquete 120 214
```

## Qué hace el comando

El comando realiza un análisis detallado del cálculo de precios para una salida de paquete:

1. **Información general**: Muestra datos del paquete, fechas, ganancia/comisión
2. **Cálculo de noches**: Determina la cantidad de noches según fecha salida/regreso
3. **Servicios incluidos**: Lista todos los servicios del paquete y su costo total
4. **Análisis por habitación**: Para cada habitación disponible en la salida muestra:
   - Precio por noche
   - Precio total de habitación (noches × precio_noche)
   - Servicios incluidos
   - Costo base (habitación + servicios)
   - Factor de ganancia/comisión aplicado
   - **Precio de venta final** (lo que paga el cliente)
   - Cupo disponible

5. **Resumen**:
   - **Habitación más barata**: Indica cuál habitación da el `precio_venta_total_min`
   - **Habitación más cara**: Indica cuál habitación da el `precio_venta_total_max`
   - Verifica si coinciden con `precio_venta_sugerido_min/max` de la salida
   - Lista ordenada de todas las habitaciones por precio

## Fórmula de cálculo

```
Precio de Venta = (Precio_Habitación × Noches + Servicios) × (1 + Ganancia/100)
```

Donde:
- **Precio_Habitación**: Precio por noche de la habitación específica
- **Noches**: Días entre fecha_salida y fecha_regreso
- **Servicios**: Suma de precios de servicios incluidos en el paquete
- **Ganancia**: Porcentaje de ganancia (para paquetes propios) o comisión (para no propios)

## Ejemplo de salida

```
================================================================================
HABITACION MAS BARATA (precio_venta_total_min)
================================================================================
Hotel: VICTOR HUGO
Habitacion ID: 18
Tipo: doble
Precio de venta: $1170.0000
Cupo disponible: 6

[OK] Coincide con precio_venta_sugerido_min (1170.00)

================================================================================
RESUMEN DE TODAS LAS HABITACIONES (ordenadas por precio)
================================================================================
1. VICTOR HUGO - Habitacion 18 (doble): $1170.0000
2. Hotel Prueba 3 - Habitacion 12 (doble): $1261.0000
3. Hard Rock Rio - Habitacion 1 (single): $1716.0000
4. Hard Rock Rio - Habitacion 2 (doble): $1807.0000
5. Hard Rock Rio - Habitacion 3 (triple): $16640.0000
```

## Ubicación del comando

El comando se encuentra en:
```
apps/paquete/management/commands/analizar_paquete.py
```

## Utilidad

Este comando es útil para:
- Verificar que los cálculos de `precio_venta_sugerido_min/max` sean correctos
- Identificar qué habitación específica corresponde al precio más bajo/alto
- Debugging de problemas de precios
- Validar que la lógica de negocio esté funcionando correctamente
- Comparar precios entre diferentes habitaciones de un mismo paquete
