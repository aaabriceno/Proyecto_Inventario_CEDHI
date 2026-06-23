# Crea los 2 accesos directos del escritorio pedidos para el CEDHI:
#   1. "Iniciar Sistema CEDHI"  -> corre iniciar_sistema.bat (levanta Docker + abre el navegador)
#   2. "ERPNext CEDHI"          -> abre la app ya corriendo en modo ventana limpia (sin barra de navegador)
# Ejecutar UNA SOLA VEZ en la laptop del CEDHI (clic derecho > Ejecutar con PowerShell).

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Desktop = [Environment]::GetFolderPath("Desktop")
$AppUrl = "http://inventario.localhost:8080"

# Detecta el navegador instalado (prioriza Edge, que viene con Windows).
$BrowserPath = $null
foreach ($candidate in @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
)) {
    if (Test-Path $candidate) { $BrowserPath = $candidate; break }
}
if (-not $BrowserPath) {
    Write-Host "No se encontro Chrome ni Edge instalado. Instale uno de los dos antes de continuar."
    exit 1
}

$IconPath = Join-Path $ScriptDir "cedhi.ico"
if (-not (Test-Path $IconPath)) {
    Write-Host "Aviso: no se encontro cedhi.ico junto a este script. Los accesos directos usaran el icono por defecto."
    Write-Host "(Para el icono del CEDHI, convierta Isotipo_principal.png a .ico y coloquelo aqui como cedhi.ico)"
}

$WshShell = New-Object -ComObject WScript.Shell

# Acceso directo 1: Iniciar Sistema
$Shortcut1 = $WshShell.CreateShortcut("$Desktop\Iniciar Sistema CEDHI.lnk")
$Shortcut1.TargetPath = Join-Path $ScriptDir "iniciar_sistema.bat"
$Shortcut1.WorkingDirectory = $ScriptDir
$Shortcut1.WindowStyle = 7  # minimizada
if (Test-Path $IconPath) { $Shortcut1.IconLocation = $IconPath }
$Shortcut1.Description = "Inicia el Sistema de Inventario CEDHI"
$Shortcut1.Save()

# Acceso directo 2: ERPNext CEDHI (ventana de app, sin barra de navegador)
$Shortcut2 = $WshShell.CreateShortcut("$Desktop\ERPNext CEDHI.lnk")
$Shortcut2.TargetPath = $BrowserPath
$Shortcut2.Arguments = "--app=$AppUrl --start-maximized"
$Shortcut2.WorkingDirectory = $ScriptDir
if (Test-Path $IconPath) { $Shortcut2.IconLocation = $IconPath }
$Shortcut2.Description = "Abre el Sistema de Inventario CEDHI"
$Shortcut2.Save()

Write-Host ""
Write-Host "Listo. Se crearon 2 accesos directos en el Escritorio:"
Write-Host "  1. Iniciar Sistema CEDHI  (doble clic para encender el sistema)"
Write-Host "  2. ERPNext CEDHI          (doble clic para abrir la app, una vez encendida)"
