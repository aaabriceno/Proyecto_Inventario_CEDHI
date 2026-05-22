# Usa la versión exacta que descargaste previamente
FROM frappe/erpnext:v16.18.3

# Cambiamos al usuario frappe por seguridad
USER frappe

# Esto descarga tu app, corrige los nombres y la instala en Python automáticamente
RUN bench get-app inventario_cedhi https://github.com/MaycolZx/Proyecto_Inventario_CEDHI
