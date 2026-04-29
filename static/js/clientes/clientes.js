document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarCliente');
    const estadoSelect = document.getElementById('estadoCliente');
    const vendedorSelect = document.getElementById('vendedorCliente');
    
    if (!input && !estadoSelect && !vendedorSelect) return;

    function applyFilters() {
        const q = (input && input.value ? input.value : '').trim();
        const estado = (estadoSelect && estadoSelect.value ? estadoSelect.value : '').trim();
        const vendedor = (vendedorSelect && vendedorSelect.value ? vendedorSelect.value : '').trim();
        
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q);
        else url.searchParams.delete('q');
        
        if (estado) url.searchParams.set('estado', estado);
        else url.searchParams.delete('estado');
        
        if (vendedor) url.searchParams.set('vendedor', vendedor);
        else url.searchParams.delete('vendedor');

        // Guardar información de que venimos de una búsqueda para restaurar el foco
        if (document.activeElement === input) {
            sessionStorage.setItem('searchFocus', 'buscarCliente');
        }
        
        window.location.href = url.toString();
    }

    // Restaurar foco si venimos de una búsqueda
    if (input && sessionStorage.getItem('searchFocus') === 'buscarCliente') {
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

    if (vendedorSelect) {
        vendedorSelect.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }
});
