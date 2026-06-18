# Imagen base de ERPNext v15 (misma serie que el bench de desarrollo).
# La app inventario_cedhi esta hecha para v15; NO usar v16 (rompe compatibilidad).
FROM frappe/erpnext:v15.99.1

USER frappe

# Descarga e instala la app inventario_cedhi (branch develop) dentro del bench.
# get-app deja la app en apps/ y la registra en el entorno Python.
RUN bench get-app --branch develop inventario_cedhi https://github.com/aaabriceno/Proyecto_Inventario_CEDHI.git
