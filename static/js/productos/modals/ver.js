(function () {
    'use strict';

    function estadoLabel(activo) {
        return activo ? 'Activo' : 'Inactivo';
    }

    function stockNivel(stock, amarillo, rojo) {
        if (stock <= rojo) return 'rojo';
        if (stock <= amarillo) return 'amarillo';
        return 'verde';
    }

    function stockBadgeHtml(stock, amarillo, rojo) {
        const nivel = stockNivel(stock, amarillo, rojo);
        const cls = nivel === 'rojo' ? 'badge-stock badge-stock-rojo' : (nivel === 'amarillo' ? 'badge-stock badge-stock-amarillo' : 'badge-stock badge-stock-verde');
        return `<span class="${cls}">${stock}</span>`;
    }

    $(document).ready(function () {
        $(document).on('click', '.btn-ver-producto', function (e) {
            e.preventDefault();
            const id = $(this).data('producto-id');
            if (!id) return;

            $.ajax({
                url: `/productos/${id}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#verProductoCodigo').text(data.codigo || '—');
                    $('#verProductoNombre').text(data.nombre || '—');
                    $('#verProductoDescripcion').text(data.descripcion || '—');
                    $('#verProductoPrecioUnidad').text(data.precio_unidad || '0.00');
                    $('#verProductoPrecioCompraUnidad').text(data.precio_compra_unidad || '0.00');
                    $('#verProductoPrecioCaja').text(data.precio_caja || '0.00');
                    $('#verProductoPrecioCompraCaja').text(data.precio_compra_caja || '0.00');

                    const activo = !!data.activo;
                    $('#verProductoEstado').html(
                        activo
                            ? '<span class="badge-estado badge-estado-activo"><i class="fas fa-check-circle"></i> Activo</span>'
                            : '<span class="badge-estado badge-estado-inactivo"><i class="fas fa-times-circle"></i> Inactivo</span>'
                    );

                    const stock = Number(data.stock_unidades ?? 0);
                    const amarillo = Number(data.stock_umbral_amarillo ?? 10);
                    const rojo = Number(data.stock_umbral_rojo ?? 3);
                    $('#verProductoStock').html(stockBadgeHtml(stock, amarillo, rojo));
                    $('#verProductoUmbralAmarillo').text(amarillo);
                    $('#verProductoUmbralRojo').text(rojo);

                    if (data.foto_url) {
                        $('#verProductoFoto').attr('src', data.foto_url).removeClass('d-none');
                        $('#verProductoFotoEmpty').addClass('d-none');
                    } else {
                        $('#verProductoFoto').attr('src', '').addClass('d-none');
                        $('#verProductoFotoEmpty').removeClass('d-none');
                    }

                    $('#modalVerProducto').modal('show');
                },
                error: function () {
                    alert('Error al cargar el producto');
                }
            });
        });

        $('#modalVerProducto').on('hidden.bs.modal', function () {
            $('#verProductoFoto').attr('src', '').addClass('d-none');
            $('#verProductoFotoEmpty').removeClass('d-none');
            $('#verProductoEstado').text('—');
            $('#verProductoStock').text('—');
        });
    });
})();
