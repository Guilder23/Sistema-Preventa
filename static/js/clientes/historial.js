(function () {
    'use strict';

    $(document).ready(function () {
        $('#historialPedidosAccordion')
            .on('show.bs.collapse', '.collapse', function () {
                $(this).closest('.historial-pedido').addClass('is-open');
            })
            .on('hide.bs.collapse', '.collapse', function () {
                $(this).closest('.historial-pedido').removeClass('is-open');
            });
    });
})();
