@echo off
echo ============================================
echo    GROUP TOURS - Iniciando servidor
echo ============================================
echo.

REM Verificar si existe un entorno virtual
if exist ..\env_group_tours\Scripts\activate.bat (
    echo [OK] Entorno virtual encontrado: ..\env_group_tours
    call ..\env_group_tours\Scripts\activate.bat
    goto :run_server
)

if exist venv\Scripts\activate.bat (
    echo [OK] Entorno virtual encontrado: venv
    call venv\Scripts\activate.bat
    goto :run_server
)

if exist env\Scripts\activate.bat (
    echo [OK] Entorno virtual encontrado: env
    call env\Scripts\activate.bat
    goto :run_server
)

if exist .venv\Scripts\activate.bat (
    echo [OK] Entorno virtual encontrado: .venv
    call .venv\Scripts\activate.bat
    goto :run_server
)

REM Si no se encuentra entorno virtual
echo [ADVERTENCIA] No se encontro un entorno virtual.
echo.
echo Opciones:
echo   1. Presiona Ctrl+C para cancelar y crear un entorno virtual
echo   2. Presiona cualquier tecla para continuar sin entorno virtual
echo.
echo Para crear un entorno virtual ejecuta:
echo   python -m venv venv
echo   venv\Scripts\activate.bat
echo   pip install -r GroupTours\requirements.txt
echo.
pause
echo.

:run_server
echo [INFO] Navegando a la carpeta del proyecto...
cd GroupTours

echo [INFO] Ejecutando migraciones pendientes...
python manage.py migrate

echo.
echo [INFO] Iniciando servidor de desarrollo...
echo [INFO] El servidor estara disponible en: http://127.0.0.1:8000
echo.
echo Presiona Ctrl+C para detener el servidor
echo.
python manage.py runserver

pause
