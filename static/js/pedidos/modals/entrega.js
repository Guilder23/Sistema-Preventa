(function () {
    'use strict';

    function renderDetalles(detalles) {
        const body = document.getElementById('entregaDetallesBody');
        if (!body) return;
        body.innerHTML = '';

        (detalles || []).forEach((d) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${d.producto__nombre || ''}</td>
                <td class="text-center">${d.cantidad}</td>
                <td class="text-center">
                    <input
                        type="number"
                        min="0"
                        max="${d.cantidad}"
                        class="form-control form-control-sm text-center js-cant-entregada"
                        name="cantidad_entregada_${d.id}"
                        value="${d.cantidad}"
                        required
                    >
                </td>
            `;
            body.appendChild(tr);
        });
    }

    function toggleModo(resultado) {
        const motivo = document.getElementById('entregaMotivo');
        const inputs = document.querySelectorAll('#entregaDetallesBody .js-cant-entregada');

        if (resultado === 'no_entregado') {
            inputs.forEach((inp) => {
                inp.value = '0';
                inp.setAttribute('readonly', 'readonly');
            });
            if (motivo) motivo.setAttribute('required', 'required');
            return;
        }

        if (motivo) motivo.removeAttribute('required');
        inputs.forEach((inp) => {
            inp.removeAttribute('readonly');
            const max = parseInt(inp.getAttribute('max') || '0', 10) || 0;
            if (resultado === 'entregado_completo') {
                inp.value = String(max);
                inp.setAttribute('readonly', 'readonly');
            }
        });

        if (resultado === 'entregado_parcial') {
            inputs.forEach((inp) => inp.removeAttribute('readonly'));
        }
    }

    $(document).ready(function () {
        let pedidoId = null;

        $(document).on('click', '.btn-registrar-entrega', function (e) {
            e.preventDefault();
            pedidoId = $(this).data('pedido-id');
            const label = $(this).data('pedido-label') || '';
            $('#entregaPedidoLabel').text(label);
            $('#entregaResultado').val('entregado_completo');
            $('#entregaMotivo').val('');

            if (!pedidoId) return;
            $.ajax({
                url: `/pedidos/${pedidoId}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    renderDetalles(data.detalles || []);
                    // rellenar fechas
                    $('#entregaPedidoFecha').text(data.fecha || '—');
                    if (data.fecha_vendido) {
                        try {
                            const dv = new Date(data.fecha_vendido);
                            const ddv = ('0' + dv.getDate()).slice(-2);
                            const mmv = ('0' + (dv.getMonth() + 1)).slice(-2);
                            const yyyyv = dv.getFullYear();
                            const hh = ('0' + dv.getHours()).slice(-2);
                            const min = ('0' + dv.getMinutes()).slice(-2);
                            $('#entregaPedidoFechaVendido').text(`${ddv}/${mmv}/${yyyyv} ${hh}:${min}`);
                        } catch (e) {
                            $('#entregaPedidoFechaVendido').text(data.fecha_vendido || '—');
                        }
                    } else {
                        $('#entregaPedidoFechaVendido').text('—');
                    }
                    toggleModo('entregado_completo');
                    $('#modalRegistrarEntrega').modal('show');
                },
                error: function () {
                    alert('No se pudo cargar el pedido');
                }
            });
        });

        $('#entregaResultado').on('change', function () {
            toggleModo($(this).val());
        });

        $('#formRegistrarEntrega').on('submit', function () {
            if (!pedidoId) return;
            $(this).attr('action', `/pedidos/${pedidoId}/entrega/`);
        });

        $('#modalRegistrarEntrega').on('hidden.bs.modal', function () {
            const body = document.getElementById('entregaDetallesBody');
            if (body) body.innerHTML = '';
            pedidoId = null;
        });
    });
})();
