(function () {
    'use strict';

    let clienteId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-eliminar-cliente', function (e) {
            e.preventDefault();
            clienteId = $(this).data('cliente-id');
            const nombre = $(this).data('cliente-nombre') || '';
            $('#eliminarClienteNombre').text(nombre);
            $('#modalEliminarCliente').modal('show');
        });

        $('#formEliminarCliente').on('submit', function () {
            if (!clienteId) return;
            $(this).attr('action', '/clientes/' + clienteId + '/eliminar/');
        });
    });
})();
