document.addEventListener('DOMContentLoaded', function () {
    const transferForm = document.getElementById('transferForm');
    const originSelect = document.querySelector('select[name="origen"]');
    const destinationSelect = document.getElementById('preventistaDestino');
    const clientChecks = Array.from(document.querySelectorAll('.cliente-check'));
    const modal = $('#modalConfirmarTransferencia');
    const confirmButton = document.getElementById('confirmTransferButton');
    let approvedByUser = false;

    if (!transferForm || !destinationSelect || !modal.length || !confirmButton) return;

    transferForm.addEventListener('submit', function (event) {
        if (approvedByUser) {
            approvedByUser = false;
            return;
        }

        const selected = clientChecks.filter((checkbox) => checkbox.checked);
        if (!selected.length) {
            event.preventDefault();
            const validation = document.getElementById('transferValidation');
            if (validation) validation.hidden = false;
            return;
        }

        event.preventDefault();
        const validation = document.getElementById('transferValidation');
        if (validation) validation.hidden = true;

        const originOption = originSelect && originSelect.options[originSelect.selectedIndex];
        const destinationOption = destinationSelect.options[destinationSelect.selectedIndex];
        document.getElementById('confirmTransferOrigin').textContent = originOption ? originOption.textContent.trim() : '—';
        document.getElementById('confirmTransferDestination').textContent = destinationOption ? destinationOption.textContent.trim() : '—';
        document.getElementById('confirmTransferCount').textContent = String(selected.length);

        const clientList = document.getElementById('confirmTransferClients');
        clientList.replaceChildren();
        selected.forEach((checkbox) => {
            const row = checkbox.closest('tr');
            const name = row && row.querySelector('.transfer-client-name');
            const item = document.createElement('li');
            item.textContent = name ? name.textContent.trim() : checkbox.getAttribute('aria-label');
            clientList.appendChild(item);
        });

        modal.modal('show');
    });

    confirmButton.addEventListener('click', function () {
        approvedByUser = true;
        modal.modal('hide');
        transferForm.requestSubmit();
    });
});