# Plan de Implementación: Backoffice con SQLAdmin

## 1. Visión General
Integración de un panel de administración profesional con **SQLAdmin** sobre **FastAPI** y **SQLAlchemy 2.0 (asyncio)**, listo para funcionar tanto en entorno local como en **Render** sin requerir servicios ni bases de datos adicionales.

---

## 2. Requerimientos Clave
* **Autenticación sin base de datos:** El acceso al panel se valida mediante variables de entorno (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_SECRET_KEY`) utilizando una sesión firmada en cookies. No se persisten usuarios ni contraseñas en tablas de base de datos.
* **Navegación contextual (Dialog -> DMessage):** Al hacer clic en un registro de `Dialog`, la vista debe permitir navegar directamente al listado de `DMessage` filtrado por dicho `dialog_id`.
* **Convención de código:** Todas las constantes deben ir en mayúsculas (ej. `DEFAULT_PAGE_SIZE = 25`) y sin números mágicos.

---

## 3. Fases del Plan de Implementación

### Paso 1: Instalación de Dependencias
* **Acción:** Instalar `sqladmin` usando `uv`:
  ```bash
  uv add sqladmin
  ```
* **Objetivo:** Incorporar la biblioteca base de administración y sus componentes de renderizado (Tabler UI / Jinja2 / WTForms).

---

### Paso 2: Autenticación por Variables de Entorno (`app/admin/auth.py`)
* **Acción:** Crear la clase `AdminAuth` heredando de `AuthenticationBackend` de SQLAdmin.
* **Detalles:**
  * Valida las credenciales enviadas desde el formulario contra variables de entorno (`ADMIN_USERNAME` y `ADMIN_PASSWORD`).
  * Utiliza `ADMIN_SECRET_KEY` para firmar la cookie de sesión (`session["token"]`).
  * **Sin tablas ni persistencia en base de datos:** Cero impacto en el esquema existente.

---

### Paso 3: Vistas de Administración (`app/admin/views.py`)
* **Acción:** Definir las clases `DialogAdmin` y `DMessageAdmin` heredando de `ModelView`.
* **Configuración de `DialogAdmin`:**
  * Columnas visibles: `id`, `duuid`, `created_date`, `updated_date`, y columna de enlace a mensajes.
  * Enlace contextual: Columna formateada personalizada (o acción) que genere el link directo a `/admin/dmessage/list?dialog_id={id}` para ver los mensajes de esa conversación.
  * Búsqueda por `duuid`.
  * Ordenamiento por fechas e ID.
* **Configuración de `DMessageAdmin`:**
  * Columnas visibles: `id`, `dialog_id`, `type`, `model`, `text` (recortado en lista), `created_date`.
  * Filtros laterales por `type`, `dialog_id`, y fecha.
  * Vista de detalle (`column_details_list`) para inspeccionar el texto completo y el JSON de `usage` (tokens y tiempos).
  * Paginación definida con constante en mayúsculas (ej. `PAGE_SIZE = 25`).

---

### Paso 4: Inicialización y Montaje en FastAPI (`app/main.py`)
* **Acción:**
  * Instanciar `Admin(app, engine, authentication_backend=auth_backend, title="Backoffice")`.
  * Registrar las vistas con `admin.add_view(DialogAdmin)` y `admin.add_view(DMessageAdmin)`.
* **Objetivo:** Publicar la ruta `/admin` en la misma aplicación FastAPI y puerto, garantizando compatibilidad total con Render.

---

### Paso 5: Pruebas y Verificación
* **Acción:**
  * Iniciar la app localmente con `uvicorn app.main:app`.
  * Probar inicio de sesión con las credenciales de entorno.
  * Verificar que el listado de `Dialog` cargue paginado.
  * Probar el clic en un `Dialog` y comprobar que filtre correctamente los `DMessage` asociados.
  * Probar filtros laterales y vista de detalle en `DMessage`.
