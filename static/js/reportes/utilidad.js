document.addEventListener('DOMContentLoaded', function () {
    const periodSelect = document.getElementById('utilidadPeriodo');
    const startDate = document.getElementById('utilidadDesde');
    const endDate = document.getElementById('utilidadHasta');
    const preventistaSelect = document.querySelector('#utilidadFilters select[name="preventista"]');
    const filtersForm = document.getElementById('utilidadFilters');

    if (!periodSelect || !startDate || !endDate || !filtersForm) return;

    let previousPeriod = periodSelect.value;

    function updateDateInputs() {
        const customRange = periodSelect.value === 'personalizado';
        startDate.disabled = !customRange;
        endDate.disabled = !customRange;
        startDate.required = customRange;
        endDate.required = customRange;
    }

    function submitWhenReady() {
        if (periodSelect.value === 'personalizado') {
            if (!startDate.value || !endDate.value) return;
            if (startDate.value > endDate.value) {
                endDate.setCustomValidity('La fecha Hasta debe ser igual o posterior a Desde.');
                endDate.reportValidity();
                return;
            }
        }
        endDate.setCustomValidity('');
        filtersForm.requestSubmit();
    }

    periodSelect.addEventListener('change', function () {
        if (periodSelect.value === 'personalizado' && previousPeriod !== 'personalizado') {
            startDate.value = '';
            endDate.value = '';
        }
        updateDateInputs();
        previousPeriod = periodSelect.value;
        if (periodSelect.value !== 'personalizado') submitWhenReady();
    });

    if (preventistaSelect) {
        preventistaSelect.addEventListener('change', submitWhenReady);
    }

    [startDate, endDate].forEach((input) => {
        input.addEventListener('change', function () {
            if (input.value && periodSelect.value !== 'personalizado') {
                periodSelect.value = 'personalizado';
                previousPeriod = 'personalizado';
                updateDateInputs();
            }
            endDate.setCustomValidity('');
            submitWhenReady();
        });
    });

    updateDateInputs();
});