(function () {
    'use strict';

    let productoId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-bloquear-producto', function (e) {
            e.preventDefault();
            productoId = $(this).data('producto-id');
            const nombre = $(this).data('producto-nombre') || '';
            $('#bloquearProductoNombre').text(nombre);
            $('#modalBloquearProducto').modal('show');
        });

        $('#formBloquearProducto').on('submit', function () {
            if (!productoId) return;
            $(this).attr('action', `/productos/${productoId}/bloquear/`);
        });
    });
})();
