document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarProducto');
    const estadoSelect = document.getElementById('estadoProducto');
    const stockSelect = document.getElementById('stockProducto');
    if (!input && !estadoSelect && !stockSelect) return;

    function applyFilters() {
        const q = (input && input.value ? input.value : '').trim();
        const estado = (estadoSelect && estadoSelect.value ? estadoSelect.value : '').trim();
        const stock = (stockSelect && stockSelect.value ? stockSelect.value : '').trim();
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q);
        else url.searchParams.delete('q');
        if (estado) url.searchParams.set('estado', estado);
        else url.searchParams.delete('estado');
        if (stock) url.searchParams.set('stock', stock);
        else url.searchParams.delete('stock');
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

    if (stockSelect) {
        stockSelect.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }
});
