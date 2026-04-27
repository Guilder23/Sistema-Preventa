(function () {
    'use strict';

    let pedidoId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-marcar-vendido', function (e) {
            e.preventDefault();
            pedidoId = $(this).data('pedido-id');
            const label = $(this).data('pedido-label') || '';
            $('#vendidoPedidoLabel').text(label);
            if (!pedidoId) {
                $('#modalMarcarVendido').modal('show');
                return;
            }
            // cargar datos para mostrar fechas
            $.ajax({
                url: `/pedidos/${pedidoId}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#vendidoPedidoFecha').text(data.fecha || '—');
                    if (data.fecha_entrega_estimada) {
                        try {
                            const d = new Date(data.fecha_entrega_estimada);
                            const dd = ('0' + d.getDate()).slice(-2);
                            const mm = ('0' + (d.getMonth() + 1)).slice(-2);
                            const yyyy = d.getFullYear();
                            $('#vendidoPedidoFechaEntrega').text(`${dd}/${mm}/${yyyy}`);
                        } catch (e) {
                            $('#vendidoPedidoFechaEntrega').text(data.fecha_entrega_estimada || '—');
                        }
                    } else {
                        $('#vendidoPedidoFechaEntrega').text('—');
                    }
                    if (data.fecha_vendido) {
                        try {
                            const dv = new Date(data.fecha_vendido);
                            const ddv = ('0' + dv.getDate()).slice(-2);
                            const mmv = ('0' + (dv.getMonth() + 1)).slice(-2);
                            const yyyyv = dv.getFullYear();
                            const hh = ('0' + dv.getHours()).slice(-2);
                            const min = ('0' + dv.getMinutes()).slice(-2);
                            $('#vendidoPedidoFechaVendido').text(`${ddv}/${mmv}/${yyyyv} ${hh}:${min}`);
                        } catch (e) {
                            $('#vendidoPedidoFechaVendido').text(data.fecha_vendido || '—');
                        }
                    } else {
                        $('#vendidoPedidoFechaVendido').text('—');
                    }
                    $('#modalMarcarVendido').modal('show');
                },
                error: function () {
                    $('#modalMarcarVendido').modal('show');
                }
            });
        });

        $('#formMarcarVendido').on('submit', function () {
            if (!pedidoId) return;
            $(this).attr('action', `/pedidos/${pedidoId}/vendido/`);
        });
    });
})();
