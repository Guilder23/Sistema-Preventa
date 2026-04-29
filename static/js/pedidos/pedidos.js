document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarPedido');
    const estadoSelect = document.getElementById('estadoPedido');
    const rolSelect = document.getElementById('rolPedido');
    const fechaDesdeInput = document.getElementById('fechaDesdePedido');
    const fechaHastaInput = document.getElementById('fechaHastaPedido');
    const pedidoTabs = document.getElementById('pedidoTabs');
    
    if (!input && !estadoSelect && !rolSelect && !fechaDesdeInput && !fechaHastaInput && !pedidoTabs) return;

    let activeTab = (pedidoTabs && pedidoTabs.dataset.tab ? pedidoTabs.dataset.tab : 'pendientes').trim();
    if (activeTab !== 'pendientes' && activeTab !== 'anteriores') activeTab = 'pendientes';

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
        
        url.searchParams.set('tab', activeTab);

        // Guardar información de que venimos de una búsqueda para restaurar el foco
        if (document.activeElement === input) {
            sessionStorage.setItem('searchFocus', 'buscarPedido');
        }
        
        window.location.href = url.toString();
    }

    // Restaurar foco si venimos de una búsqueda
    if (input && sessionStorage.getItem('searchFocus') === 'buscarPedido') {
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

    if (pedidoTabs) {
        pedidoTabs.querySelectorAll('.pedido-tab-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                activeTab = this.dataset.tab;
                applyFilters();
            });
        });
    }
});
