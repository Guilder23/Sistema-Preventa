(function () {
    'use strict';

    let pedidoId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-marcar-vendido', function (e) {
            e.preventDefault();
            pedidoId = $(this).data('pedido-id');
            const label = $(this).data('pedido-label') || '';
            $('#vendidoPedidoLabel').text(label);
            $('#modalMarcarVendido').modal('show');
        });

        $('#formMarcarVendido').on('submit', function () {
            if (!pedidoId) return;
            $(this).attr('action', `/pedidos/${pedidoId}/vendido/`);
        });
    });
})();
