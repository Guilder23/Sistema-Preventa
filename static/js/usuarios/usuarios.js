/* ============================================================================
   USUARIOS.JS - Orquestador Principal
   ============================================================================ */

document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscar');
    const estadoSelect = document.getElementById('estado');
    const rolSelect = document.getElementById('rolFiltro');
    if (!input && !estadoSelect && !rolSelect) return;

    function applyFilters() {
        const buscar = (input && input.value ? input.value : '').trim();
        const estado = (estadoSelect && estadoSelect.value ? estadoSelect.value : '').trim();
        const rol = (rolSelect && rolSelect.value ? rolSelect.value : '').trim();
        const url = new URL(window.location.href);
        if (buscar) url.searchParams.set('buscar', buscar);
        else url.searchParams.delete('buscar');
        if (estado) url.searchParams.set('estado', estado);
        else url.searchParams.delete('estado');
        if (rol) url.searchParams.set('rol', rol);
        else url.searchParams.delete('rol');
        window.location.href = url.toString();
    }

    let t;
    if (input) {
        input.addEventListener('input', function () {
            clearTimeout(t);
            t = setTimeout(applyFilters, 250);
        });
    }

    if (estadoSelect) {
        estadoSelect.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }

    if (rolSelect) {
        rolSelect.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }

    // Mantener compatibilidad con modales existentes
    if (typeof inicializarModalCrear === 'function') inicializarModalCrear();
    if (typeof inicializarModalVer === 'function') inicializarModalVer();
    if (typeof inicializarModalEditar === 'function') inicializarModalEditar();
    if (typeof inicializarModalEliminar === 'function') inicializarModalEliminar();
});

/**
 * Búsqueda en tiempo real (frontend)
 */
function inicializarBusquedaFrontend() {
    const inputBuscar = document.getElementById('buscar');
    
    if (inputBuscar) {
        let timeoutId;
        inputBuscar.addEventListener('input', function() {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                aplicarFiltrosFrontend();
            }, 200);
        });
    }
}

/**
 * Filtros automáticos (frontend)
 */
function inicializarFiltrosFrontend() {
    const filtroEstado = document.getElementById('estado');
    const filtroRol = document.getElementById('rolFiltro');
    
    if (filtroEstado) {
        filtroEstado.addEventListener('change', () => aplicarFiltrosFrontend());
    }
    
    if (filtroRol) {
        filtroRol.addEventListener('change', () => aplicarFiltrosFrontend());
    }
}

/**
 * Aplica filtros y búsqueda en el frontend
 */
function aplicarFiltrosFrontend() {
    const buscar = (document.getElementById('buscar')?.value || '').toLowerCase().trim();
    const estado = document.getElementById('estado')?.value || '';
    const rol = document.getElementById('rolFiltro')?.value || '';
    
    const filas = document.querySelectorAll('.tabla-usuarios tbody tr');
    let contadorVisible = 0;
    
    filas.forEach(fila => {
        if (fila.querySelector('td[colspan]')) {
            return;
        }
        
        const textoFila = fila.textContent.toLowerCase();
        const estadoFila = fila.querySelector('.badge-estado-activo, .badge-estado-inactivo');
        const rolBadge = fila.querySelector('.badge-rol');
        
        let mostrar = true;
        
        if (buscar && !textoFila.includes(buscar)) {
            mostrar = false;
        }
        
        if (estado && estadoFila) {
            if (estado === 'activo' && !estadoFila.classList.contains('badge-estado-activo')) {
                mostrar = false;
            }
            if (estado === 'inactivo' && !estadoFila.classList.contains('badge-estado-inactivo')) {
                mostrar = false;
            }
        }
        
        if (rol && rolBadge) {
            const rolEnBadge = rolBadge.getAttribute('data-rol') || '';
            if (rolEnBadge !== rol) {
                mostrar = false;
            }
        }
        
        fila.style.display = mostrar ? '' : 'none';
        if (mostrar) contadorVisible++;
    });
    
    mostrarMensajeSinResultados(contadorVisible, buscar, estado, rol);
}

/**
 * Actualiza el contador de usuarios visibles
 */
function actualizarContador(cantidad) {
    const contadorElement = document.querySelector('.card-title .badge');
    if (contadorElement) {
        contadorElement.textContent = cantidad;
    }
}

/**
 * Muestra un mensaje cuando no hay resultados
 */
function mostrarMensajeSinResultados(cantidad, buscar, estado, rol) {
    const tbody = document.querySelector('.tabla-usuarios tbody');
    if (!tbody) return;
    
    const mensajeAnterior = tbody.querySelector('.mensaje-sin-resultados');
    if (mensajeAnterior) {
        mensajeAnterior.remove();
    }
    
    if (cantidad > 0) return;
    
    let mensaje = 'No se encontraron usuarios';
    const filtros = [];
    
    if (buscar) {
        filtros.push(`que coincidan con "${buscar}"`);
    }
    if (estado) {
        filtros.push(`con estado "${estado}"`);
    }
    if (rol) {
        const rolesMap = {
            'administrador': 'Administrador',
                'supervisor': 'Supervisor',
                'repartidor': 'Repartidor',
                'preventista': 'Preventista'
        };
        filtros.push(`con rol "${rolesMap[rol] || rol}"`);
    }
    
    if (filtros.length > 0) {
        mensaje += ' ' + filtros.join(' y ');
    }
    
    const filaMensaje = document.createElement('tr');
    filaMensaje.className = 'mensaje-sin-resultados';
    filaMensaje.innerHTML = `
        <td colspan="7" class="text-center py-4">
            <i class="fas fa-search fa-3x text-muted mb-2" style="display: block;"></i>
            <p class="text-muted mb-0"><strong>${mensaje}</strong></p>
            <p class="text-muted small">Intente con otros criterios de búsqueda</p>
        </td>
    `;
    
    tbody.appendChild(filaMensaje);
}