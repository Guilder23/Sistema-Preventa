(function () {
    'use strict';

    function formatMoney(value) {
        const number = Number(value || 0);
        return number.toFixed(2);
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function badgeForTipo(tipo, tipoDisplay) {
        const isEntrada = tipo === 'entrada';
        const klass = isEntrada ? 'badge-success' : 'badge-danger';
        const icon = isEntrada ? 'fa-circle-plus' : 'fa-circle-minus';
        return `<span class="badge ${klass} badge-pill"><i class="fas ${icon}"></i> ${tipoDisplay || ''}</span>`;
    }

    function renderMovimientos(movimientos) {
        const tbody = document.getElementById('inventarioMovimientosBody');
        if (!tbody) return;
        if (!movimientos || !movimientos.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">Sin movimientos registrados</td></tr>';
            return;
        }

        tbody.innerHTML = movimientos.map(function (mov) {
            return `
                <tr>
                    <td>${mov.fecha || '-'}</td>
                    <td>${badgeForTipo(mov.tipo, mov.tipo_display)}</td>
                    <td class="text-center font-weight-bold">${mov.cantidad}</td>
                    <td class="text-center">${mov.stock_anterior}</td>
                    <td class="text-center">${mov.stock_nuevo}</td>
                    <td>${escapeHtml(mov.usuario || '-')}</td>
                    <td>${escapeHtml(mov.motivo || '-')}</td>
                    <td>Bs ${formatMoney(mov.valor_compra_total)}</td>
                </tr>
            `;
        }).join('');
    }

    function setModalData(data) {
        $('#inventarioProductoId').val(data.id);
        $('#inventarioProductoTitulo').text(`${data.codigo} - ${data.nombre}`);
        $('#inventarioStockActual').text(data.stock_actual ?? 0);
        $('#inventarioPrecioCompra').text(formatMoney(data.precio_compra_unidad));
        $('#inventarioValorCompra').text(formatMoney(data.valor_inventario_compra));
        $('#formAjustarInventario').attr('action', `/productos/${data.id}/inventario/ajustar/`);
        renderMovimientos(data.movimientos || []);
        $('#inventarioCantidad').val('');
        $('#inventarioMotivo').val('');
        $('#inventarioTipo').val('entrada');
    }

    $(document).ready(function () {
        $(document).on('click', '.btn-ajustar-inventario-producto', function (e) {
            e.preventDefault();
            const id = $(this).data('producto-id');
            if (!id) return;

            $.ajax({
                url: `/productos/${id}/inventario/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    setModalData(data);
                    $('#modalAjustarInventario').modal('show');
                },
                error: function () {
                    alert('No se pudo cargar el inventario del producto');
                }
            });
        });

        $('#inventarioTipo').on('change', function () {
            const tipo = $(this).val();
            const ayuda = $('#inventarioAyuda');
            if (tipo === 'salida') {
                ayuda.text('La reducción no puede dejar el stock en negativo.');
            } else {
                ayuda.text('Agrega unidades al stock y registra el motivo.');
            }
        });

        $('#modalAjustarInventario').on('hidden.bs.modal', function () {
            $('#inventarioProductoId').val('');
            $('#inventarioProductoTitulo').text('Producto');
            $('#inventarioMovimientosBody').html('<tr><td colspan="8" class="text-center text-muted py-4">Sin movimientos registrados</td></tr>');
            $('#inventarioCantidad').val('');
            $('#inventarioMotivo').val('');
            $('#inventarioTipo').val('entrada');
            $('#formAjustarInventario').removeAttr('action');
            $('#inventarioAyuda').text('El stock no se puede reducir por debajo de cero.');
        });
    });
})();
