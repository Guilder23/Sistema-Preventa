(function () {
    'use strict';

    let clienteId = null;

    $(document).ready(function () {
        $(document).on('click', '.btn-bloquear-cliente', function (e) {
            e.preventDefault();
            clienteId = $(this).data('cliente-id');
            const nombre = $(this).data('cliente-nombre') || '';
            $('#bloquearClienteNombre').text(nombre);
            $('#modalBloquearCliente').modal('show');
        });

        $('#formBloquearCliente').on('submit', function () {
            if (!clienteId) return;
            $(this).attr('action', `/clientes/${clienteId}/bloquear/`);
        });
    });
})();
