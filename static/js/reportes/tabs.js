document.addEventListener('DOMContentLoaded', function () {
    const reportesTabs = document.getElementById('reportesTabs');
    const filtroForm = document.getElementById('filtro-reportes');
    const tipoInput = filtroForm ? filtroForm.querySelector('input[name="tipo"]') : null;

    if (!reportesTabs || !filtroForm || !tipoInput) return;

    let activeTab = (reportesTabs.dataset.tab || 'general').trim();

    // Mostrar/ocultar grupos de filtros y habilitar/desabilitar inputs
    function updateFiltersVisibility() {
        const grupoGeneral = document.querySelector('.filtro-grupo-general');
        const grupoDespacho = document.querySelector('.filtro-grupo-despacho');
        const grupoDevoluciones = document.querySelector('.filtro-grupo-devoluciones');

        // Ocultar y desabilitar todos primero
        [grupoGeneral, grupoDespacho, grupoDevoluciones].forEach(grupo => {
            if (!grupo) return;
            grupo.style.display = 'none';
            const inputs = grupo.querySelectorAll('input, select');
            inputs.forEach(input => input.disabled = true);
        });

        // Mostrar y habilitar el grupo activo
        if (activeTab === 'general' && grupoGeneral) {
            grupoGeneral.style.display = 'block';
            const inputs = grupoGeneral.querySelectorAll('input, select');
            inputs.forEach(input => input.disabled = false);
        } else if (activeTab === 'despacho' && grupoDespacho) {
            grupoDespacho.style.display = 'block';
            const inputs = grupoDespacho.querySelectorAll('input, select');
            inputs.forEach(input => input.disabled = false);
        } else if (activeTab === 'devoluciones' && grupoDevoluciones) {
            grupoDevoluciones.style.display = 'block';
            const inputs = grupoDevoluciones.querySelectorAll('input, select');
            inputs.forEach(input => input.disabled = false);
        }
    }

    // Cambiar pestaña activa y aplicar filtros
    function switchTab(tab) {
        if (tab !== 'general' && tab !== 'despacho' && tab !== 'devoluciones') return;
        activeTab = tab;
        
        // Actualizar botones
        const buttons = reportesTabs.querySelectorAll('[data-tab]');
        buttons.forEach(btn => {
            if (btn.dataset.tab === tab) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Actualizar valor del input tipo
        tipoInput.value = tab;
        
        // Mostrar/ocultar grupos de filtros y habilitar/desabilitar
        updateFiltersVisibility();
        
        // Aplicar filtros
        filtroForm.submit();
    }

    // Event listeners para los botones de pestaña
    const tabButtons = reportesTabs.querySelectorAll('[data-tab]');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            switchTab(btn.dataset.tab);
        });
    });

    // Inicializar visibilidad de filtros
    updateFiltersVisibility();
});
