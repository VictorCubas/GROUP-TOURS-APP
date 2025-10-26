# Instrucciones de Ejecución - Group Tours

## Scripts Disponibles

### 🚀 `run.bat` - Ejecutar el Servidor

Script principal para iniciar el proyecto Django.

**Uso:**
```bash
run.bat
```

**Funcionalidades:**
- Detecta automáticamente el entorno virtual (`venv`, `env`, o `.venv`)
- Activa el entorno virtual
- Navega a la carpeta `GroupTours`
- Ejecuta migraciones pendientes
- Inicia el servidor en `http://127.0.0.1:8000`

---

### ⚙️ `setup.bat` - Configuración Inicial

Script para configurar el entorno de desarrollo desde cero.

**Uso:**
```bash
setup.bat
```

**Funcionalidades:**
- Crea un entorno virtual en la carpeta `venv`
- Actualiza `pip` a la última versión
- Instala todas las dependencias desde `GroupTours/requirements.txt`
- Ejecuta las migraciones de la base de datos
- Prepara el proyecto para su ejecución

---

## Flujo de Trabajo Recomendado

### Primera vez (Configuración inicial)

1. Ejecutar el script de configuración:
   ```bash
   setup.bat
   ```

2. Esperar a que termine la instalación

3. Ejecutar el servidor:
   ```bash
   run.bat
   ```

### Ejecuciones posteriores

Simplemente ejecutar:
```bash
run.bat
```

---

## Comandos Manuales (Alternativa)

Si prefieres ejecutar los comandos manualmente:

### Activar entorno virtual:
```bash
venv\Scripts\activate.bat
```

### Navegar al proyecto:
```bash
cd GroupTours
```

### Ejecutar servidor:
```bash
python manage.py runserver
```

### Ejecutar migraciones:
```bash
python manage.py migrate
```

### Crear migraciones:
```bash
python manage.py makemigrations
```

### Crear superusuario:
```bash
python manage.py createsuperuser
```

---

## Notas

- El servidor estará disponible en: `http://127.0.0.1:8000`
- Para detener el servidor: presiona `Ctrl+C`
- El entorno virtual debe estar activado para ejecutar comandos Django
- Los archivos `.bat` solo funcionan en Windows

## Requisitos Previos

- Python 3.8+ instalado
- Git (para clonar el repositorio)
- Acceso a la terminal/CMD de Windows
