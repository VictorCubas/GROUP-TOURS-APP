"""
Script de ejemplo para actualizar fechas de salida usando la API

Demuestra cómo adelantar una fecha de salida de 20-12-2025 a 06-12-2025

Uso:
    python ejemplo_actualizar_fecha_salida.py
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/paquete/salidas"


def listar_salidas(paquete_id=None):
    """Lista todas las salidas o filtra por paquete_id"""
    url = API_ENDPOINT + "/"
    params = {}
    if paquete_id:
        params['paquete_id'] = paquete_id
    
    print(f"\n{'='*60}")
    print("🔍 Listando salidas...")
    print(f"{'='*60}")
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        salidas = response.json()
        print(f"✅ Encontradas {len(salidas)} salidas\n")
        
        for salida in salidas:
            print(f"  ID: {salida['id']}")
            print(f"  Fecha Salida: {salida['fecha_salida']}")
            print(f"  Fecha Regreso: {salida['fecha_regreso']}")
            print(f"  Activo: {salida['activo']}")
            print(f"  {'─'*50}")
        
        return salidas
    else:
        print(f"❌ Error al listar salidas: {response.status_code}")
        print(response.text)
        return []


def obtener_detalle_salida(salida_id):
    """Obtiene el detalle completo de una salida"""
    url = f"{API_ENDPOINT}/{salida_id}/"
    
    print(f"\n{'='*60}")
    print(f"📋 Obteniendo detalle de salida {salida_id}...")
    print(f"{'='*60}")
    
    response = requests.get(url)
    
    if response.status_code == 200:
        salida = response.json()
        print(f"✅ Salida encontrada:")
        print(f"  ID: {salida['id']}")
        print(f"  Paquete: {salida.get('paquete', {}).get('nombre', 'N/A')}")
        print(f"  Fecha Salida: {salida['fecha_salida']}")
        print(f"  Fecha Regreso: {salida['fecha_regreso']}")
        print(f"  Costo Base Desde: {salida['costo_base_desde']} {salida.get('moneda', {}).get('codigo', '')}")
        print(f"  Cupo: {salida.get('cupo', 'N/A')}")
        print(f"  Activo: {salida['activo']}")
        
        return salida
    else:
        print(f"❌ Error al obtener detalle: {response.status_code}")
        print(response.text)
        return None


def actualizar_fechas_salida(salida_id, fecha_salida, fecha_regreso=None):
    """
    Actualiza las fechas de una salida específica
    
    Args:
        salida_id: ID de la salida a actualizar
        fecha_salida: Nueva fecha de salida (formato: YYYY-MM-DD)
        fecha_regreso: Nueva fecha de regreso (formato: YYYY-MM-DD) - opcional
    """
    url = f"{API_ENDPOINT}/{salida_id}/actualizar-fechas/"
    
    payload = {
        "fecha_salida": fecha_salida
    }
    
    if fecha_regreso:
        payload["fecha_regreso"] = fecha_regreso
    
    print(f"\n{'='*60}")
    print(f"📅 Actualizando fechas de salida {salida_id}...")
    print(f"{'='*60}")
    print(f"📤 Enviando:")
    print(json.dumps(payload, indent=2))
    
    response = requests.patch(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ {data['mensaje']}")
        print(f"  Paquete: {data['paquete']}")
        print(f"  Nueva Fecha Salida: {data['fecha_salida']}")
        print(f"  Nueva Fecha Regreso: {data['fecha_regreso']}")
        
        return data
    else:
        print(f"\n❌ Error al actualizar fechas: {response.status_code}")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
        except:
            print(response.text)
        
        return None


def ejemplo_adelantar_fecha():
    """
    Ejemplo: Adelantar una salida de 20-12-2025 a 06-12-2025
    """
    print("\n" + "="*60)
    print("🚀 EJEMPLO: Adelantar fecha de salida")
    print("="*60)
    print("Escenario: Una salida programada para el 20-12-2025")
    print("           necesita adelantarse al 06-12-2025")
    print("="*60)
    
    # 1. Listar salidas disponibles
    salidas = listar_salidas()
    
    if not salidas:
        print("\n⚠️  No hay salidas disponibles para actualizar.")
        print("   Primero crea algunas salidas o verifica que el servidor esté corriendo.")
        return
    
    # 2. Seleccionar la primera salida como ejemplo
    salida_ejemplo = salidas[0]
    salida_id = salida_ejemplo['id']
    fecha_actual = salida_ejemplo['fecha_salida']
    
    print(f"\n📍 Usando salida ID {salida_id} como ejemplo")
    print(f"   Fecha actual: {fecha_actual}")
    
    # 3. Obtener detalle completo antes de actualizar
    print("\n" + "─"*60)
    print("ANTES DE LA ACTUALIZACIÓN:")
    print("─"*60)
    salida_antes = obtener_detalle_salida(salida_id)
    
    # 4. Actualizar fechas
    nueva_fecha_salida = "2025-12-06"
    nueva_fecha_regreso = "2025-12-15"
    
    resultado = actualizar_fechas_salida(
        salida_id, 
        nueva_fecha_salida, 
        nueva_fecha_regreso
    )
    
    if resultado:
        # 5. Verificar cambios
        print("\n" + "─"*60)
        print("DESPUÉS DE LA ACTUALIZACIÓN:")
        print("─"*60)
        salida_despues = obtener_detalle_salida(salida_id)
        
        print("\n" + "="*60)
        print("✅ ACTUALIZACIÓN EXITOSA!")
        print("="*60)


def ejemplo_cambiar_solo_salida():
    """
    Ejemplo: Cambiar solo la fecha de salida, manteniendo fecha de regreso
    """
    print("\n" + "="*60)
    print("🚀 EJEMPLO: Cambiar solo fecha de salida")
    print("="*60)
    
    salidas = listar_salidas()
    
    if not salidas:
        print("\n⚠️  No hay salidas disponibles.")
        return
    
    salida_id = salidas[0]['id']
    nueva_fecha_salida = "2025-12-10"
    
    # Solo actualizar fecha_salida, sin enviar fecha_regreso
    actualizar_fechas_salida(salida_id, nueva_fecha_salida)


def ejemplo_retrasar_fecha():
    """
    Ejemplo: Retrasar una salida a una fecha futura
    """
    print("\n" + "="*60)
    print("🚀 EJEMPLO: Retrasar fecha de salida")
    print("="*60)
    print("Escenario: Posponer una salida por problemas logísticos")
    print("="*60)
    
    salidas = listar_salidas()
    
    if not salidas:
        print("\n⚠️  No hay salidas disponibles.")
        return
    
    salida_id = salidas[0]['id']
    nueva_fecha_salida = "2026-01-15"
    nueva_fecha_regreso = "2026-01-22"
    
    actualizar_fechas_salida(salida_id, nueva_fecha_salida, nueva_fecha_regreso)


def menu_interactivo():
    """Menú interactivo para probar la API"""
    while True:
        print("\n" + "="*60)
        print("🎯 MENÚ DE PRUEBAS - API ACTUALIZAR FECHAS SALIDA")
        print("="*60)
        print("1. Listar todas las salidas")
        print("2. Ver detalle de una salida")
        print("3. Actualizar fechas de una salida")
        print("4. Ejemplo: Adelantar fecha (20-12-2025 → 06-12-2025)")
        print("5. Ejemplo: Cambiar solo fecha de salida")
        print("6. Ejemplo: Retrasar fecha")
        print("0. Salir")
        print("="*60)
        
        opcion = input("\nSelecciona una opción: ").strip()
        
        if opcion == "1":
            listar_salidas()
        
        elif opcion == "2":
            salida_id = input("Ingresa el ID de la salida: ").strip()
            if salida_id.isdigit():
                obtener_detalle_salida(int(salida_id))
            else:
                print("❌ ID inválido")
        
        elif opcion == "3":
            salida_id = input("Ingresa el ID de la salida: ").strip()
            fecha_salida = input("Nueva fecha de salida (YYYY-MM-DD): ").strip()
            fecha_regreso = input("Nueva fecha de regreso (YYYY-MM-DD, Enter para omitir): ").strip()
            
            if salida_id.isdigit() and fecha_salida:
                actualizar_fechas_salida(
                    int(salida_id), 
                    fecha_salida, 
                    fecha_regreso if fecha_regreso else None
                )
            else:
                print("❌ Datos inválidos")
        
        elif opcion == "4":
            ejemplo_adelantar_fecha()
        
        elif opcion == "5":
            ejemplo_cambiar_solo_salida()
        
        elif opcion == "6":
            ejemplo_retrasar_fecha()
        
        elif opcion == "0":
            print("\n👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")
        
        input("\nPresiona Enter para continuar...")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     SCRIPT DE PRUEBA - ACTUALIZACIÓN DE FECHAS DE SALIDA    ║
║                       GroupTours API                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Verificar que el servidor esté corriendo
        response = requests.get(f"{BASE_URL}/api/paquete/salidas/", timeout=5)
        print(f"✅ Servidor conectado - Status: {response.status_code}")
        
        # Ejecutar menú interactivo
        menu_interactivo()
        
    except requests.exceptions.ConnectionError:
        print(f"""
❌ ERROR: No se puede conectar al servidor

Por favor, asegúrate de que el servidor Django esté corriendo:

    python manage.py runserver

Luego ejecuta este script nuevamente.
        """)
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario. ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

