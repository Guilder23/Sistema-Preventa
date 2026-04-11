(function () {
    'use strict';

    function setPreview(url) {
        const img = document.getElementById('editFotoPreview');
        if (!img) return;
        if (!url) {
            img.src = '';
            img.classList.add('d-none');
            return;
        }
        img.src = url;
        img.classList.remove('d-none');
    }

    function previewFile(inputEl) {
        const img = document.getElementById('editFotoPreview');
        if (!inputEl || !img) return;
        const file = inputEl.files && inputEl.files[0];
        if (!file) return;
        const url = URL.createObjectURL(file);
        img.src = url;
        img.classList.remove('d-none');
        img.onload = function () {
            try { URL.revokeObjectURL(url); } catch (e) { /* ignore */ }
        };
    }

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

                    $('#editStockUnidades').val(data.stock_unidades ?? 0);
                    $('#editStockAmarillo').val(data.stock_umbral_amarillo ?? 10);
                    $('#editStockRojo').val(data.stock_umbral_rojo ?? 3);

                    // Preview de imagen actual
                    setPreview(data.foto_url || null);
                    $('#editFoto').val('');

                    $('#modalEditarProducto').modal('show');
                },
                error: function () {
                    alert('Error al cargar el producto');
                }
            });
        });

        $('#editFoto').on('change', function () {
            previewFile(this);
        });

        $('#formEditarProducto').on('submit', function (e) {
            const id = $('#editProductoId').val();
            if (!id) {
                e.preventDefault();
                return false;
            }
            $(this).attr('action', `/productos/${id}/editar/`);
        });

        $('#modalEditarProducto').on('hidden.bs.modal', function () {
            setPreview(null);
            $('#editFoto').val('');
        });
    });
})();
