(function () {
    'use strict';

    function renderResumenResumen(bodyId, totalItemsId, totalAumentaId, resumen) {
        var body = document.getElementById(bodyId);
        if (!body) return;

        body.innerHTML = '';
        var productos = (resumen && resumen.productos) ? resumen.productos : [];

        var totalItemsNode = document.getElementById(totalItemsId);
        var totalAumentaNode = document.getElementById(totalAumentaId);
        if (totalItemsNode) totalItemsNode.textContent = (resumen && resumen.total_items) || 0;
        if (totalAumentaNode) totalAumentaNode.textContent = (resumen && resumen.total_aumenta) || 0;

        if (!productos.length) {
            var trEmpty = document.createElement('tr');
            trEmpty.innerHTML = '<td colspan="4" class="text-center text-muted">No hay items pendientes para reponer</td>';
            body.appendChild(trEmpty);
            return;
        }

        productos.forEach(function (p) {
            var tr = document.createElement('tr');
            tr.innerHTML = [
                '<td>' + (p.producto || '-') + '</td>',
                '<td class="text-center">' + (p.stock_actual || 0) + '</td>',
                '<td class="text-center text-success font-weight-bold">+' + (p.aumenta || 0) + '</td>',
                '<td class="text-center font-weight-bold">' + (p.stock_final || 0) + '</td>'
            ].join('');
            body.appendChild(tr);
        });
    }

    $(document).on('click', '.btn-reponer-devolucion', function () {
        var devolucionId = $(this).data('devolucion-id');
        var pedidoId = $(this).data('pedido-id');

        var form = document.getElementById('formReponerDevolucion');
        if (!form || !devolucionId) return;

        form.action = '/devoluciones/' + devolucionId + '/reponer/';

        var pedidoNode = document.getElementById('repPedidoId');
        if (pedidoNode) {
            pedidoNode.textContent = '#' + (pedidoId || '-');
        }

        fetch('/devoluciones/' + devolucionId + '/resumen-reponer/', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                renderResumenResumen('repResumenBody', 'repTotalItems', 'repTotalAumenta', data.resumen || {});
                $('#modalReponerDevolucion').modal('show');
            })
            .catch(function () {
                window.alert('No se pudo cargar el resumen de reposicion');
            });
    });
})();
