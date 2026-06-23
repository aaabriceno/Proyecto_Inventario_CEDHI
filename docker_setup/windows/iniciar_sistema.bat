@echo off
title Sistema de Inventario CEDHI - Iniciando...
setlocal

set "COMPOSE_DIR=%~dp0.."
set "APP_URL=http://inventario.localhost:8080"

echo ============================================
echo  Sistema de Inventario CEDHI
echo  Iniciando, por favor espere...
echo ============================================
echo.

REM 1. Verificar que Docker este instalado.
where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Docker no esta instalado en esta computadora.
    echo Descargue e instale Docker Desktop desde:
    echo   https://www.docker.com/products/docker-desktop/
    echo Luego abralo una vez manualmente antes de usar este acceso directo.
    echo.
    pause
    exit /b 1
)

REM 2. Verificar que Docker Desktop esta corriendo. Si no, arrancarlo y esperar.
docker info >nul 2>&1
if errorlevel 1 (
    if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        echo.
        echo ERROR: Docker esta instalado pero no se encontro Docker Desktop.exe
        echo en la ruta esperada. Abra Docker Desktop manualmente y vuelva a
        echo intentar este acceso directo.
        echo.
        pause
        exit /b 1
    )
    echo Iniciando Docker Desktop, esto puede tardar un minuto...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    goto esperar_docker_loop
)
goto docker_listo

:esperar_docker_loop
set /a INTENTOS=0

:esperar_docker
set /a INTENTOS+=1
if %INTENTOS% GTR 24 goto docker_timeout

timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if errorlevel 1 goto esperar_docker
goto docker_listo

:docker_timeout
echo.
echo ERROR: Docker Desktop no respondio tras 2 minutos.
echo Abralo manualmente y revise que haya terminado de iniciar.
echo.
pause
exit /b 1

:docker_listo

echo Docker listo. Levantando los servicios del sistema...
cd /d "%COMPOSE_DIR%"
docker compose up -d

echo.
echo Esperando que la aplicacion termine de cargar...

REM 2. Esperar a que el frontend responda en el puerto 8080 antes de abrir el navegador.
set /a INTENTOS_APP=0

:esperar_app
set /a INTENTOS_APP+=1
if %INTENTOS_APP% GTR 60 goto app_timeout

timeout /t 3 /nobreak >nul
curl -s -o nul --fail %APP_URL% >nul 2>nul
if errorlevel 1 goto esperar_app

echo.
echo Sistema listo. Abriendo...
start "" %APP_URL%
echo.
echo Puede cerrar esta ventana.
timeout /t 5
goto fin

:app_timeout
echo.
echo ERROR: La aplicacion no respondio tras varios minutos.
echo Revise que los contenedores hayan terminado de iniciar con:
echo   docker compose logs --tail 50
echo.
pause
exit /b 1

:fin
endlocal
