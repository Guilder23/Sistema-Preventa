document.addEventListener('DOMContentLoaded', function () {
    const filtersForm = document.getElementById('transferFilters');
    const originSelect = document.querySelector('select[name="origen"]');
    const selectPage = document.getElementById('selectPage');
    const clientChecks = Array.from(document.querySelectorAll('.cliente-check'));
    const selectedCount = document.getElementById('selectedCount');

    if (originSelect && filtersForm) {
        originSelect.addEventListener('change', function () {
            filtersForm.requestSubmit();
        });
    }

    function updateSelectedCount() {
        const selected = clientChecks.filter((checkbox) => checkbox.checked).length;
        if (selectedCount) selectedCount.textContent = String(selected);
    }

    if (selectPage) {
        selectPage.addEventListener('change', function () {
            clientChecks.forEach((checkbox) => {
                checkbox.checked = selectPage.checked;
            });
            updateSelectedCount();
        });
    }

    clientChecks.forEach((checkbox) => {
        checkbox.addEventListener('change', function () {
            if (selectPage) {
                selectPage.checked = clientChecks.length > 0 && clientChecks.every((item) => item.checked);
            }
            updateSelectedCount();
        });
    });
});