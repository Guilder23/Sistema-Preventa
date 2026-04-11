(function () {
    'use strict';

    function estadoLabel(estado) {
        if (estado === 'anulado') return 'Anulado';
        if (estado === 'vendido') return 'Vendido';
        return 'Pendiente';
    }

    $(document).ready(function () {
        $(document).on('click', '.btn-ver-pedido', function (e) {
            e.preventDefault();
            const id = $(this).data('pedido-id');
            if (!id) return;

            $.ajax({
                url: `/pedidos/${id}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#verPedidoCliente').text(data.cliente || '—');
                    $('#verPedidoPreventista').text(data.preventista || '—');
                    $('#verPedidoFecha').text(data.fecha || '—');
                    $('#verPedidoEstado').text(estadoLabel(data.estado));
                    $('#verPedidoTotal').text(data.total || '0.00');
                    $('#verPedidoObs').text(data.observacion || '—');

                    const body = $('#verPedidoDetalles');
                    body.empty();
                    (data.detalles || []).forEach((d) => {
                        const precio = d.precio_unitario ?? '0.00';
                        const subtotal = d.subtotal ?? '0.00';
                        body.append(`
                            <tr>
                                <td>${d.producto__nombre}</td>
                                <td>Bs ${precio}</td>
                                <td>${d.cantidad}</td>
                                <td>Bs ${subtotal}</td>
                            </tr>
                        `);
                    });

                    $('#modalVerPedido').modal('show');
                },
                error: function () {
                    alert('Error al cargar el pedido');
                }
            });
        });

        $('#modalVerPedido').on('hidden.bs.modal', function () {
            $('#verPedidoDetalles').empty();
        });
    });
})();
