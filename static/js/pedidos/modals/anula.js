(function () {
    'use strict';

    let pedidoId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-anular-pedido', function (e) {
            e.preventDefault();
            pedidoId = $(this).data('pedido-id');
            const label = $(this).data('pedido-label') || '';
            $('#anularPedidoLabel').text(label);
            $('#modalAnularPedido').modal('show');
        });

        $('#formAnularPedido').on('submit', function () {
            if (!pedidoId) return;
            $(this).attr('action', `/pedidos/${pedidoId}/anular/`);
        });
    });
})();
