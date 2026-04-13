document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarPedido');
    const estadoSelect = document.getElementById('estadoPedido');
    const rolSelect = document.getElementById('rolPedido');
    const fechaDesdeInput = document.getElementById('fechaDesdePedido');
    const fechaHastaInput = document.getElementById('fechaHastaPedido');
    if (!input && !estadoSelect && !rolSelect && !fechaDesdeInput && !fechaHastaInput) return;

    function applyFilters() {
        const q = (input && input.value ? input.value : '').trim();
        const estado = (estadoSelect && estadoSelect.value ? estadoSelect.value : '').trim();
        const rol = (rolSelect && rolSelect.value ? rolSelect.value : '').trim();
        const fechaDesde = (fechaDesdeInput && fechaDesdeInput.value ? fechaDesdeInput.value : '').trim();
        const fechaHasta = (fechaHastaInput && fechaHastaInput.value ? fechaHastaInput.value : '').trim();
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q);
        else url.searchParams.delete('q');
        if (estado) url.searchParams.set('estado', estado);
        else url.searchParams.delete('estado');
        if (rol) url.searchParams.set('rol', rol);
        else url.searchParams.delete('rol');
        if (fechaDesde) url.searchParams.set('fecha_desde', fechaDesde);
        else url.searchParams.delete('fecha_desde');
        if (fechaHasta) url.searchParams.set('fecha_hasta', fechaHasta);
        else url.searchParams.delete('fecha_hasta');
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

    if (fechaDesdeInput) {
        fechaDesdeInput.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }

    if (fechaHastaInput) {
        fechaHastaInput.addEventListener('change', function () {
            clearTimeout(t);
            applyFilters();
        });
    }
});
