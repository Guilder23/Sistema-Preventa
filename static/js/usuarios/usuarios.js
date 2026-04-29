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

        // Guardar información de que venimos de una búsqueda para restaurar el foco
        if (document.activeElement === input) {
            sessionStorage.setItem('searchFocus', 'buscarUsuario');
        }
        
        window.location.href = url.toString();
    }

    // Restaurar foco si venimos de una búsqueda
    if (input && sessionStorage.getItem('searchFocus') === 'buscarUsuario') {
        input.focus();
        const val = input.value;
        input.value = '';
        input.value = val; // Poner el cursor al final
        sessionStorage.removeItem('searchFocus');
    }

    let t;
    if (input) {
        input.addEventListener('input', function () {
            clearTimeout(t);
            t = setTimeout(applyFilters, 1000);
        });

        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                clearTimeout(t);
                applyFilters();
            }
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
});
