(function () {
    'use strict';

    $(document).ready(function () {
        $(document).on('click', '.btn-editar-producto', function (e) {
            e.preventDefault();
            const id = $(this).data('producto-id');
            if (!id) return;

            $.ajax({
                url: `/productos/${id}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#editProductoId').val(data.id);
                    $('#editCodigo').val(data.codigo);
                    $('#editNombre').val(data.nombre);
                    $('#editDescripcion').val(data.descripcion || '');
                    $('#editPrecioUnidad').val(data.precio_unidad || '0');
                    $('#editPrecioMayor').val(data.precio_mayor || '0');
                    $('#editPrecioCaja').val(data.precio_caja || '0');
                    $('#editActivo').prop('checked', !!data.activo);

                    $('#modalEditarProducto').modal('show');
                },
                error: function () {
                    alert('Error al cargar el producto');
                }
            });
        });

        $('#formEditarProducto').on('submit', function (e) {
            const id = $('#editProductoId').val();
            if (!id) {
                e.preventDefault();
                return false;
            }
            $(this).attr('action', `/productos/${id}/editar/`);
        });
    });
})();
