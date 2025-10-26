@echo off
echo ============================================
echo    GROUP TOURS - Configuracion Inicial
echo ============================================
echo.

REM Verificar si ya existe un entorno virtual
if exist venv\ (
    echo [ADVERTENCIA] Ya existe una carpeta 'venv'
    echo.
    choice /C SN /M "Deseas eliminarla y crear una nueva"
    if errorlevel 2 goto :cancel
    if errorlevel 1 (
        echo [INFO] Eliminando entorno virtual anterior...
        rmdir /s /q venv
    )
)

echo [INFO] Creando entorno virtual...
python -m venv venv

if not exist venv\Scripts\activate.bat (
    echo [ERROR] No se pudo crear el entorno virtual
    echo Verifica que Python este instalado correctamente
    pause
    exit /b 1
)

echo [OK] Entorno virtual creado exitosamente
echo.

echo [INFO] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [INFO] Actualizando pip...
python -m pip install --upgrade pip

echo.
echo [INFO] Instalando dependencias desde requirements.txt...
pip install -r GroupTours\requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Hubo un problema al instalar las dependencias
    pause
    exit /b 1
)

echo.
echo [OK] Dependencias instaladas correctamente
echo.

echo [INFO] Navegando a la carpeta del proyecto...
cd GroupTours

echo [INFO] Ejecutando migraciones...
python manage.py migrate

echo.
echo ============================================
echo    Configuracion completada exitosamente
echo ============================================
echo.
echo Para iniciar el servidor, ejecuta:
echo   run.bat
echo.
echo O manualmente:
echo   venv\Scripts\activate.bat
echo   cd GroupTours
echo   python manage.py runserver
echo.
pause
goto :end

:cancel
echo [INFO] Operacion cancelada
pause

:end
