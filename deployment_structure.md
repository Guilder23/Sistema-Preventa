# Estructura de despliegue - SistemaPreventaOficial

Este archivo describe la estructura del despliegue en el servidor Hostinger, con comentarios para entender cada sección y facilitar el mantenimiento.

---

## 1. Ubicaciones principales del servidor

- `/root`
  - Home del usuario root.
  - Contiene archivos de configuración del servidor cuando se usa root.

- `/home/guilder`
  - Home del usuario que ejecuta la aplicación.
  - Aquí está el proyecto, los entornos virtuales, backups, logs y scripts.

- `/home/guilder/projects/SistemaPreventaOficial`
  - Carpeta raíz del proyecto Django desplegado.
  - Contiene el código fuente, los archivos estáticos generados, los medios y el entorno virtual.

- `/etc/nginx`
  - Directorio donde vive la configuración global de Nginx.
  - Aquí están los sitios disponibles y habilitados.

- `/etc/systemd/system`
  - Directorio donde está el servicio systemd que gestiona Gunicorn para la app.

---

## 2. Configuración de Nginx

### Archivos clave
- `/etc/nginx/nginx.conf`
  - Configuración principal de Nginx.
  - Carga los sitios de `sites-enabled` y la configuración global.

- `/etc/nginx/sites-available/sistema-preventa`
  - Configuración de servidor para la app.
  - Define proxy a Gunicorn, alias estáticos y media.

- `/etc/nginx/sites-enabled/sistema-preventa`
  - Enlace simbólico activo hacia `sites-available/sistema-preventa`.

### Comentarios importantes
- `location /static/`:
  - Sirve archivos estáticos desde `/home/guilder/projects/SistemaPreventaOficial/staticfiles/`.

- `location /media/`:
  - Sirve archivos de usuario/media desde `/home/guilder/projects/SistemaPreventaOficial/media/`.

- `proxy_pass http://sistema_preventa;`:
  - Redirige las peticiones a Gunicorn en `127.0.0.1:8001`.

---

## 3. Servicio systemd para Gunicorn

### Archivo clave
- `/etc/systemd/system/sistema-preventa.service`

### Contenido y propósito
- `User=guilder`
  - El proceso se ejecuta como usuario `guilder`, no como root.

- `WorkingDirectory=/home/guilder/projects/SistemaPreventaOficial`
  - Directorio base desde donde arranca Gunicorn.

- `Environment="PATH=/home/guilder/projects/SistemaPreventaOficial/venv/bin"`
  - Usa el entorno virtual correcto del proyecto.

- `ExecStart=/home/guilder/projects/SistemaPreventaOficial/venv/bin/gunicorn ... sistemaPreventa.wsgi:application`
  - Ejecuta Gunicorn con el módulo WSGI de Django.
  - El binding se hace en `127.0.0.1:8001`.

---

## 4. Proyecto Django en el servidor

### Raíz del proyecto
- `/home/guilder/projects/SistemaPreventaOficial`

### Subcarpetas principales
- `apps/`
  - Contiene las apps Django locales del proyecto (`clientes`, `productos`, `pedidos`, `usuarios`, etc.).

- `sistemaPreventa/`
  - Contiene la configuración Django principal (`settings.py`, `urls.py`, `wsgi.py`, `asgi.py`).

- `templates/`
  - Plantillas HTML compartidas por Django.

- `static/`
  - Archivos estáticos fuente (CSS, JS, imágenes) del proyecto.

- `staticfiles/`
  - Archivos estáticos recolectados listos para servir vía Nginx.

- `media/`
  - Archivos subidos por usuarios o generados en tiempo de ejecución.

- `venv/`
  - Entorno virtual Python usado para ejecutar la aplicación.

### Comentarios de mantenimiento
- Siempre actualizar el código en `apps/` y `sistemaPreventa/`.
- Volver a ejecutar `collectstatic` para regenerar `staticfiles/` cuando haya cambios en `static/`.
- Revisar `media/` si hay uploads o assets dinámicos que deben sincronizarse.

---

## 5. Base de datos

### Comentario general
- El servicio systemd indica que el proyecto depende de PostgreSQL:
  - `After=network.target postgresql.service`
- La base de datos no está dentro de la carpeta del proyecto.
- Se gestiona externamente, fuera de `/home/guilder/projects/SistemaPreventaOficial`.

### Nota de mantenimiento
- Revisar `DATABASES` en `sistemaPreventa/settings.py` para ver conexión y credenciales.
- Si se actualiza el servidor de DB, no se mueve la carpeta del proyecto.

---

## 6. Flujo de solicitudes

1. El usuario accede al servidor por HTTP/HTTPS.
2. Nginx recibe la petición.
3. Si la solicitud es `/static/` o `/media/`, Nginx sirve el archivo directamente.
4. Si es otra ruta, Nginx proxy_pass a Gunicorn en `127.0.0.1:8001`.
5. Gunicorn ejecuta Django y devuelve la respuesta.
6. Django puede leer/escribir datos vía PostgreSQL externo.

---

## 7. Puntos útiles para mantenimiento

- Para reiniciar el servicio:
  - `systemctl restart sistema-preventa`

- Para verificar errores de Nginx:
  - `journalctl -u nginx` o revisar `/var/log/nginx/error.log`

- Para verificar Gunicorn y Django:
  - `journalctl -u sistema-preventa`

- Para verificar que Nginx está usando el sitio correcto:
  - `ls -l /etc/nginx/sites-enabled/`

- Para cambios de código:
  1. Actualizar archivos en `/home/guilder/projects/SistemaPreventaOficial`
  2. Activar entorno virtual y ejecutar migraciones si es necesario
  3. Ejecutar `python manage.py collectstatic`
  4. Reiniciar `systemctl restart sistema-preventa`
  5. Probar la aplicación

---

## 8. Árbol de directorios touchados y configurados

Este árbol muestra las rutas que se tocaron para la configuración actual y las rutas que se deberían cambiar si se actualiza el despliegue.

```
/root                  # Home de root, no usado directamente por la app
/home/guilder          # Home del usuario de despliegue
  ├─ backups/          # Backups del usuario, no parte del proyecto directo
  ├─ envs/             # Entornos virtuales o ambientes auxiliares
  ├─ logs/             # Logs personalizados del usuario
  ├─ projects/         # Carpeta de proyectos desplegados
  │   ├─ SistemaPreventaOficial/  # Proyecto Django actual en producción
  │   │   ├─ .git/      # Repo Git del proyecto
  │   │   ├─ apps/      # Apps Django locales del proyecto
  │   │   ├─ media/     # Archivos subidos y media servida por Nginx
  │   │   ├─ static/    # Archivos estáticos fuente del proyecto
  │   │   ├─ staticfiles/ # Archivos estáticos recolectados para Nginx
  │   │   ├─ templates/ # Plantillas Django
  │   │   ├─ venv/      # Entorno virtual Python usado por Gunicorn
  │   │   └─ sistemaPreventa/ # Configuración Django principal
  │   └─ SistemaPreventaPrueba/ # Proyecto de prueba
  └─ scripts/          # Scripts de despliegue o mantenimiento
/etc/nginx/            # Configuración de Nginx
  ├─ nginx.conf        # Configuración global de Nginx
  ├─ conf.d/           # Configs adicionales de Nginx
  ├─ sites-available/  # Sitios disponibles para habilitar
  │   ├─ default
  │   └─ sistema-preventa  # Configuración de este proyecto
  └─ sites-enabled/    # Sitios habilitados activamente
      └─ sistema-preventa -> /etc/nginx/sites-available/sistema-preventa
/etc/systemd/system/   # Servicios systemd
  └─ sistema-preventa.service  # Servicio de Gunicorn para el proyecto
/etc/postgresql/       # Configuración de PostgreSQL
  └─ 16/                # Versión del servidor PostgreSQL
/var/lib/postgresql/   # Datos físicos de PostgreSQL
  └─ 16/                # Cluster de datos de PostgreSQL
```

### Comentarios de mantenimiento sobre el árbol
- Cambios de código y estáticos: principalmente en `/home/guilder/projects/SistemaPreventaOficial`.
- Configuración de Nginx: `/etc/nginx/sites-available/sistema-preventa` y su enlace en `sites-enabled`.
- Servicio de arranque y Gunicorn: `/etc/systemd/system/sistema-preventa.service`.
- Base de datos PostgreSQL: `/etc/postgresql/16` y `/var/lib/postgresql/16`.
- Si se migrara el proyecto completo, estas rutas son las que deberán actualizarse en primer lugar.

