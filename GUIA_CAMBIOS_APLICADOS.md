# Guía de Cambios Aplicados - Sistema Preventa

**Fecha:** 04 de Julio de 2026  
**Rama:** `dev`  
**Cambios principales:** Comentar modo oscuro e icono de historial de pedidos

---

## Resumen de Cambios

Se desactivó temporalmente:
1. El sistema de tema claro/oscuro
2. El botón de historial de pedidos en la sección Clientes

---

## Archivos Modificados - Rutas Completas

### 1. **Desactivar el Modo Oscuro - Context Processors**

**Ruta:** `apps/core/context_processors.py`

**Cambio:**
```python
# ANTES:
def theme_flags(request):
    """Flags globales de UI.
    En el proyecto guía esto depende del plan/empresa. Aquí se permite siempre.
    """
    return {"theme_allowed": True}

# DESPUÉS:
def theme_flags(request):
    """Flags globales de UI.
    El modo oscuro queda comentado temporalmente para mantener el sistema
    siempre en tema claro.
    """
    # return {"theme_allowed": True}
    return {"theme_allowed": False}
```

**Efecto:** Desactiva el flag global que permite el cambio de tema en el servidor.

---

### 2. **Comentar la Lógica del Tema en JavaScript**

**Ruta:** `static/js/componentes/theme.js`

**Línea:** ~11

**Cambio:**
```javascript
// ANTES:
const THEME_ALLOWED = (window.THEME_ALLOWED !== false);

if (!THEME_ALLOWED) {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
        // ignore
    }
    document.documentElement.setAttribute('data-theme', 'light');
    return;
}

// DESPUÉS:
// El modo oscuro queda comentado temporalmente.
/*
const THEME_ALLOWED = (window.THEME_ALLOWED !== false);

if (!THEME_ALLOWED) {
    try {
        localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
        // ignore
    }
    document.documentElement.setAttribute('data-theme', 'light');
    return;
}
*/

const THEME_ALLOWED = false;

if (!THEME_ALLOWED) {
```

**Efecto:** Fuerza el tema claro a nivel de JavaScript.

---

### 3. **Comentar el Script de Inicialización del Tema en Base.html**

**Ruta:** `templates/base/base.html`

**Línea:** ~14-19

**Cambio:**
```html
<!-- ANTES: -->
<script>
    (function () {
        try {
            var themeAllowed = {% if theme_allowed %}true{% else %}false{% endif %};
            window.THEME_ALLOWED = themeAllowed;

            if (!themeAllowed) {
                try { localStorage.removeItem('theme'); } catch (e) { /* ignore */ }
                document.documentElement.setAttribute('data-theme', 'light');
                return;
            }

            var theme = localStorage.getItem('theme');
            if (theme !== 'light' && theme !== 'dark') {
                // Por defecto usar 'light' en lugar de detectar el sistema
                theme = 'light';
            }
            document.documentElement.setAttribute('data-theme', theme);
        } catch (e) {
            // ignore
        }
    })();
</script>

<!-- DESPUÉS: -->
<script>
    (function () {
        try {
            // Modo oscuro comentado temporalmente.
            // var themeAllowed = {% if theme_allowed %}true{% else %}false{% endif %};
            // window.THEME_ALLOWED = themeAllowed;
            // if (!themeAllowed) {
            //     try { localStorage.removeItem('theme'); } catch (e) { /* ignore */ }
            //     document.documentElement.setAttribute('data-theme', 'light');
            //     return;
            // }

            var themeAllowed = false;
            window.THEME_ALLOWED = themeAllowed;

            if (!themeAllowed) {
                try { localStorage.removeItem('theme'); } catch (e) { /* ignore */ }
                document.documentElement.setAttribute('data-theme', 'light');
                return;
            }
```

**Efecto:** Evita que la lógica del tema se ejecute en la inicialización de la página.

---

### 4. **Comentar el Botón de Tema en la Navbar**

**Ruta:** `templates/componentes/navbar.html`

**Línea:** ~23-32 (dentro del navbar-right)

**Cambio:**
```html
<!-- ANTES: -->
<div class="navbar-right">

    <!-- Tema (modo claro/oscuro) -->
    {% if theme_allowed %}
    <div class="navbar-theme">
        <button class="navbar-icon-btn" id="themeToggleBtn" type="button" title="Modo oscuro" aria-label="Cambiar tema">
            <i class="fas fa-moon" id="themeToggleIcon"></i>
        </button>
    </div>
    {% endif %}

    <!-- Usuario -->

<!-- DESPUÉS: -->
<div class="navbar-right">

    {#
    <!-- Tema (modo claro/oscuro) -->
    {% if theme_allowed %}
    <div class="navbar-theme">
        <button class="navbar-icon-btn" id="themeToggleBtn" type="button" title="Modo oscuro" aria-label="Cambiar tema">
            <i class="fas fa-moon" id="themeToggleIcon"></i>
        </button>
    </div>
    {% endif %}
    #}

    <!-- Usuario -->
```

**Efecto:** Oculta el botón de cambio de tema en la barra de navegación superior.

---

### 5. **Comentar el Botón de Historial de Pedidos en Clientes**

**Ruta:** `templates/clientes/clientes.html`

**Línea:** ~110-116 (en la sección de acciones de la tabla)

**Cambio:**
```html
<!-- ANTES: -->
<div class="acciones-btns">
    <button type="button" class="btn btn-info btn-sm btn-ver-cliente" data-cliente-id="{{ c.id }}" title="Ver">
        <i class="fas fa-eye"></i>
    </button>
    <a class="btn btn-primary btn-sm" href="{% url 'historial_pedidos_cliente' c.id %}" title="Historial de pedidos">
        <i class="fas fa-receipt"></i>
    </a>
    <button type="button" class="btn btn-warning btn-sm btn-editar-cliente" data-cliente-id="{{ c.id }}" title="Editar">
        <i class="fas fa-edit"></i>
    </button>

<!-- DESPUÉS: -->
<div class="acciones-btns">
    <button type="button" class="btn btn-info btn-sm btn-ver-cliente" data-cliente-id="{{ c.id }}" title="Ver">
        <i class="fas fa-eye"></i>
    </button>
    {#
    <a class="btn btn-primary btn-sm" href="{% url 'historial_pedidos_cliente' c.id %}" title="Historial de pedidos">
        <i class="fas fa-receipt"></i>
    </a>
    #}
    <button type="button" class="btn btn-warning btn-sm btn-editar-cliente" data-cliente-id="{{ c.id }}" title="Editar">
        <i class="fas fa-edit"></i>
    </button>
```

**Efecto:** Oculta el icono de recibo que llevaba al historial de pedidos de cada cliente en la tabla de Clientes.

---

## Proceso de Actualización en el Servidor

### Paso a Paso - Deploy en Hostinger

**Servidor:** `187.127.45.61`  
**Ruta del proyecto:** `/home/guilder/projects/SistemaPreventaOficial`  
**Puerto:** `8001`

#### 1. Conectar al Servidor
```bash
ssh root@187.127.45.61
```

#### 2. Navegar al Proyecto
```bash
cd /home/guilder/projects/SistemaPreventaOficial
```

#### 3. Activar el Entorno Virtual
```bash
source venv/bin/activate
```

#### 4. Descargar los Cambios del Git
```bash
git pull origin dev
```

#### 5. Recopilar Archivos Estáticos
```bash
python manage.py collectstatic --noinput
```

#### 6. Verificar la Salud de la Aplicación
```bash
python manage.py check
```

#### 7. Detener el Proceso Gunicorn Anterior
```bash
# Primero, buscar el PID del proceso master
ps aux | grep gunicorn | grep SistemaPreventaOficial

# Luego, eliminar el proceso master (el que tiene --daemon)
kill <PID>
```

#### 8. Reiniciar Gunicorn
```bash
gunicorn --workers 3 --bind 127.0.0.1:8001 --timeout 60 --access-logfile - --error-logfile - sistemaPreventa.wsgi:application --daemon
```

#### 9. Verificar que Gunicorn está Corriendo
```bash
ps aux | grep gunicorn | grep SistemaPreventaOficial | grep -v grep
```

Deberías ver 4 procesos (1 master + 3 workers)

---

## Verificación Post-Actualización

### En Local (Windows)
```bash
cd C:\Users\GUILDER\Desktop\PTRABAJO\Sistema-Preventa
python manage.py check
```

### En el Servidor
```bash
# Desde /home/guilder/projects/SistemaPreventaOficial
python manage.py check

# Verificar proceso
ps aux | grep gunicorn | grep 8001
```

### En el Navegador
- Acceder a: https://distribuidorajeremy.duckdns.org/
- Presionar **Ctrl+F5** (limpiar caché)
- Verificar que no aparece el botón de tema (luna) en la navbar
- Verificar que en la tabla de Clientes desapareció el icono de recibo

---

## Rollback (Revertir los Cambios)

Si necesitas volver atrás:

```bash
# En el servidor
cd /home/guilder/projects/SistemaPreventaOficial
source venv/bin/activate

# Revertir a la rama main o al commit anterior
git checkout main
# O
git reset --hard <COMMIT_HASH>

# Reiniciar el proceso
python manage.py collectstatic --noinput
kill <PID_GUNICORN>
gunicorn --workers 3 --bind 127.0.0.1:8001 --timeout 60 --access-logfile - --error-logfile - sistemaPreventa.wsgi:application --daemon
```

---

## Notas Importantes

⚠️ **No elimines archivos**, solo comenta el código. Así es más fácil reactivar después.

⚠️ **Siempre ejecuta `collectstatic`** después de cambios en CSS/JS estáticos.

⚠️ **Siempre reinicia Gunicorn** después de cambios en Python.

⚠️ **Espera 10-30 segundos** a que los workers se reinicien antes de acceder a la URL.

⚠️ **Limpia caché del navegador** (Ctrl+F5) si aún ves cambios viejos.

---

## Git Workflow Completo

### 1. Hacer Cambios en Local
```bash
# Editar archivos en VS Code
git add .
git commit -m "Descripción del cambio"
git push origin dev
```

### 2. Actualizar en el Servidor
```bash
cd /home/guilder/projects/SistemaPreventaOficial
source venv/bin/activate
git pull origin dev
python manage.py collectstatic --noinput
kill <PID>
gunicorn --workers 3 --bind 127.0.0.1:8001 --timeout 60 --access-logfile - --error-logfile - sistemaPreventa.wsgi:application --daemon
```

---

**Última actualización:** 04/07/2026 - 08:27 UTC
