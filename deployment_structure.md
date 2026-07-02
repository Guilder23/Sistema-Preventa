# Estructura de despliegue - SistemaPreventaOficial y SistemaPreventaPrueba

Este archivo describe la estructura real del despliegue en el servidor Hostinger, con detalles de la configuración actual, los servicios activos y las rutas que deben mantenerse.

---

## 1. Visión general del servidor

- `/root`
  - Home del usuario root.
  - No se utiliza directamente para los despliegues de aplicación.

- `/home/guilder`
  - Home del usuario que ejecuta los proyectos.
  - Contiene los proyectos, los entornos virtuales y scripts.

- `/etc/nginx`
  - Configuración global de Nginx.
  - Carga los sitios habilitados desde `sites-enabled`.

- `/etc/systemd/system`
  - Servicios `systemd` que arrancan Gunicorn para cada despliegue.

- PostgreSQL:
  - Configuración: `/etc/postgresql/16`
  - Datos: `/var/lib/postgresql/16`

---

## 2. Deploy oficial - SistemaPreventaOficial

### Ubicación del proyecto
- `/home/guilder/projects/SistemaPreventaOficial`

### Configuración de Nginx
- `/etc/nginx/sites-available/sistema-preventa`
- `/etc/nginx/sites-enabled/sistema-preventa`

### Servicio Gunicorn
- `/etc/systemd/system/sistema-preventa.service`

### Bind de Gunicorn
- `127.0.0.1:8001`

### Base de datos
- Nombre: `sistema_preventa_oficial`
- Usuario: `sistema_user`
- Base de datos PostgreSQL compartida en el mismo servidor.

### URL pública
- `http://187.127.45.61`

---

## 3. Deploy de prueba - SistemaPreventaPrueba

### Ubicación del proyecto de prueba
- `/home/guilder/projects/SistemaPreventaPrueba`

### Configuración de Nginx de prueba
- `/etc/nginx/sites-available/sistema-preventa-prueba`
- `/etc/nginx/sites-enabled/sistema-preventa-prueba`

### Servicio Gunicorn de prueba
- `/etc/systemd/system/sistema-preventa-prueba.service`

### Bind de Gunicorn de prueba
- `127.0.0.1:8002`

### Base de datos de prueba
- Nombre: `sistema_preventa_prueba`
- Usuario: `sistema_user_prueba`

### URL de prueba
- `http://187.127.45.61:8081`

---

## 4. Configuración Nginx común

### Nginx principal
- `/etc/nginx/nginx.conf`
  - Configuración global de Nginx.
  - Incluye `/etc/nginx/sites-enabled/*`.

### Sitios configurados
- `sistema-preventa` (oficial)
- `sistema-preventa-prueba` (prueba)

### Comentarios importantes
- El deploy oficial sirve estáticos desde `/home/guilder/projects/SistemaPreventaOficial/staticfiles/`.
- El deploy oficial sirve media desde `/home/guilder/projects/SistemaPreventaOficial/media/`.
- El deploy de prueba sirve estáticos desde `/home/guilder/projects/SistemaPreventaPrueba/staticfiles/`.
- El deploy de prueba sirve media desde `/home/guilder/projects/SistemaPreventaPrueba/media/`.
- El deploy oficial y de prueba usan diferentes puertos Nginx y Gunicorn.

---

## 5. Servicios systemd activos

### Oficial
- `sistema-preventa.service`
  - User: `guilder`
  - WorkingDirectory: `/home/guilder/projects/SistemaPreventaOficial`
  - Gunicorn bind: `127.0.0.1:8001`

### Prueba
- `sistema-preventa-prueba.service`
  - User: `guilder`
  - WorkingDirectory: `/home/guilder/projects/SistemaPreventaPrueba`
  - Gunicorn bind: `127.0.0.1:8002`

---

## 6. Proyecto oficial: estructura de carpetas

- `/home/guilder/projects/SistemaPreventaOficial/`
  - `.git/`
  - `apps/`
  - `media/`
  - `static/`
  - `staticfiles/`
  - `templates/`
  - `venv/`
  - `sistemaPreventa/`
  - `.env`

### Comentarios de mantenimiento
- Cambios de código: `apps/` y `sistemaPreventa/`.
- Cambios estáticos: `static/` → `python manage.py collectstatic` → `staticfiles/`.
- Archivos subidos: `media/`.
- Variables sensibles: `.env` debe tener permisos seguros y ser legible por `guilder`.

---

## 7. Proyecto de prueba: estructura de carpetas

- `/home/guilder/projects/SistemaPreventaPrueba/`
  - `.git/`
  - `apps/`
  - `media/`
  - `static/`
  - `staticfiles/`
  - `templates/`
  - `venv/`
  - `sistemaPreventa/`
  - `.env`

### Comentarios de mantenimiento
- Debe ser independiente del oficial, con su propio `.env` y base de datos.
- El directorio debe ser propiedad de `guilder`.
- Si se actualiza la rama o el código, el deploy de prueba debe hacer `git pull origin dev` sin tocar el oficial.

---

## 8. PostgreSQL en el servidor

- Configuración: `/etc/postgresql/16`
- Datos: `/var/lib/postgresql/16`
- Bases de datos creadas por los despliegues:
  - `sistema_preventa_oficial`
  - `sistema_preventa_prueba`

---

## 9. Árbol de directorios actual

```
/root
/home/guilder
  ├─ backups/
  ├─ envs/
  ├─ logs/
  ├─ projects/
  │   ├─ SistemaPreventaOficial/
  │   │   ├─ .git/
  │   │   ├─ apps/
  │   │   ├─ media/
  │   │   ├─ static/
  │   │   ├─ staticfiles/
  │   │   ├─ templates/
  │   │   ├─ venv/
  │   │   └─ sistemaPreventa/
  │   └─ SistemaPreventaPrueba/
  │       ├─ .git/
  │       ├─ apps/
  │       ├─ media/
  │       ├─ static/
  │       ├─ staticfiles/
  │       ├─ templates/
  │       ├─ venv/
  │       └─ sistemaPreventa/
  └─ scripts/
/etc/nginx/
  ├─ nginx.conf
  ├─ conf.d/
  ├─ sites-available/
  │   ├─ default
  │   ├─ sistema-preventa
  │   └─ sistema-preventa-prueba
  └─ sites-enabled/
      ├─ sistema-preventa -> /etc/nginx/sites-available/sistema-preventa
      └─ sistema-preventa-prueba -> /etc/nginx/sites-available/sistema-preventa-prueba
/etc/systemd/system/
  ├─ sistema-preventa.service
  └─ sistema-preventa-prueba.service
/etc/postgresql/
  └─ 16/
/var/lib/postgresql/
  └─ 16/
```

---

## 10. Comandos útiles

- Ver estado del deploy oficial:
  - `systemctl status sistema-preventa`
- Ver estado del deploy de prueba:
  - `systemctl status sistema-preventa-prueba`
- Ver logs de ambos:
  - `journalctl -u sistema-preventa -f`
  - `journalctl -u sistema-preventa-prueba -f`
- Recargar Nginx:
  - `sudo nginx -t && sudo systemctl reload nginx`
- Reiniciar un servicio:
  - `sudo systemctl restart sistema-preventa`
  - `sudo systemctl restart sistema-preventa-prueba`

---

## 11. Notas finales

- El deploy oficial se sirve en `http://187.127.45.61`.
- El deploy de prueba se sirve en `http://187.127.45.61:8081`.
- Ambos despliegues son independientes en servicios, Nginx, puertos y bases de datos.
