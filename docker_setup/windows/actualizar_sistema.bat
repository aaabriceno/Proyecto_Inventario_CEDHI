@echo off
title Sistema de Inventario CEDHI - Actualizando...
setlocal

set "COMPOSE_DIR=%~dp0.."
set "SITE_NAME=inventario.localhost"

echo ============================================
echo  Sistema de Inventario CEDHI
echo  Actualizando a la version mas reciente...
echo ============================================
echo.
echo IMPORTANTE: esto NO borra ningun dato (articulos, movimientos,
echo usuarios). Solo descarga el codigo mas reciente y actualiza el
echo sistema. Puede tardar varios minutos.
echo.
pause

REM 1. Verificar que Docker este instalado y corriendo.
where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker no esta instalado en esta computadora.
    echo Instale Docker Desktop antes de actualizar.
    echo.
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker Desktop no esta corriendo. Abralo manualmente,
    echo espere a que la ballena quede en verde, y vuelva a intentar.
    echo.
    pause
    exit /b 1
)

cd /d "%COMPOSE_DIR%"

echo.
echo Paso 1/3: Descargando la version mas reciente y reconstruyendo...
echo (esto puede tardar varios minutos la primera vez)
echo.
docker compose build --no-cache
if errorlevel 1 (
    echo.
    echo ERROR: Fallo la descarga/reconstruccion. Revise su conexion a
    echo internet e intente de nuevo.
    echo.
    pause
    exit /b 1
)

echo.
echo Paso 2/3: Levantando los servicios actualizados...
echo.
docker compose up -d
if errorlevel 1 (
    echo.
    echo ERROR: Fallo al levantar los servicios. Revise:
    echo   docker compose logs --tail 50
    echo.
    pause
    exit /b 1
)

echo.
echo Esperando que la base de datos termine de iniciar...
timeout /t 15 /nobreak >nul

echo.
echo Paso 3/3: Aplicando los cambios a la base de datos existente...
echo.
docker compose exec backend bench --site %SITE_NAME% migrate
if errorlevel 1 (
    echo.
    echo ERROR: Fallo la migracion. Revise:
    echo   docker compose logs --tail 50
    echo Puede reintentar este mismo script.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Actualizacion completa.
echo  Use "Iniciar Sistema CEDHI" normalmente.
echo ============================================
echo.
pause

endlocal
