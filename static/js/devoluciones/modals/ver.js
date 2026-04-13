(function () {
    'use strict';

    function renderItems(items) {
        var body = document.getElementById('devItemsBody');
        if (!body) return;

        body.innerHTML = '';

        if (!items || !items.length) {
            var emptyRow = document.createElement('tr');
            emptyRow.innerHTML = '<td colspan="4" class="text-center text-muted">Sin items devueltos</td>';
            body.appendChild(emptyRow);
            return;
        }

        items.forEach(function (it) {
            var tr = document.createElement('tr');
            var rep = 'Pendiente';
            if (it.repuesto) {
                rep = 'Repuesto';
                if (it.fecha_reposicion) {
                    rep += ' (' + it.fecha_reposicion + ')';
                }
                if (it.repuesto_por) {
                    rep += ' - ' + it.repuesto_por;
                }
            }

            tr.innerHTML = [
                '<td>' + (it.producto || '-') + '</td>',
                '<td class="text-center">' + (it.cantidad_devuelta || 0) + '</td>',
                '<td>' + (it.motivo || '-') + '</td>',
                '<td>' + rep + '</td>'
            ].join('');

            body.appendChild(tr);
        });
    }

    $(document).on('click', '.btn-ver-devolucion', function (e) {
        e.preventDefault();
        var id = $(this).data('devolucion-id');
        if (!id) return;

        $.ajax({
            url: '/devoluciones/' + id + '/obtener/',
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                $('#devPedido').text('#' + (data.pedido_id || '-'));
                $('#devCliente').text(data.cliente || '-');
                $('#devRepartidor').text(data.repartidor || '-');
                $('#devTipo').text(data.tipo || '-');
                $('#devEstadoReposicion').text(data.estado_reposicion || '-');
                $('#devFecha').text(data.fecha || '-');
                $('#devMotivoGeneral').text(data.motivo_general || '-');

                renderItems(data.items || []);
                $('#modalVerDevolucion').modal('show');
            },
            error: function () {
                window.alert('Error al cargar la devolucion');
            }
        });
    });
})();
