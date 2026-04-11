document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarPedido');
    const estadoSelect = document.getElementById('estadoPedido');
    if (!input && !estadoSelect) return;

    function applyFilters() {
        const q = (input && input.value ? input.value : '').trim();
        const estado = (estadoSelect && estadoSelect.value ? estadoSelect.value : '').trim();
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q);
        else url.searchParams.delete('q');
        if (estado) url.searchParams.set('estado', estado);
        else url.searchParams.delete('estado');
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
});
