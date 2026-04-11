(function () {
    'use strict';

    function estadoLabel(activo) {
        return activo ? 'Activo' : 'Inactivo';
    }

    $(document).ready(function () {
        $(document).on('click', '.btn-ver-cliente', function (e) {
            e.preventDefault();
            const id = $(this).data('cliente-id');
            if (!id) return;

            $.ajax({
                url: `/clientes/${id}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#verClienteNombres').text(data.nombres || '—');
                    $('#verClienteApellidos').text(data.apellidos || '—');
                    $('#verClienteCiNit').text(data.ci_nit || '—');
                    $('#verClienteTelefono').text(data.telefono || '—');
                    $('#verClienteDireccion').text(data.direccion || '—');

                    const ubicacion = (data.latitud && data.longitud)
                        ? `${parseFloat(data.latitud).toFixed(5)}, ${parseFloat(data.longitud).toFixed(5)}`
                        : 'Sin ubicación';
                    $('#verClienteUbicacion').text(ubicacion);
                    $('#verClienteEstado').text(estadoLabel(!!data.activo));

                    if (data.foto_url) {
                        $('#verClienteFoto').attr('src', data.foto_url).removeClass('d-none');
                        $('#verClienteFotoEmpty').addClass('d-none');
                    } else {
                        $('#verClienteFoto').attr('src', '').addClass('d-none');
                        $('#verClienteFotoEmpty').removeClass('d-none');
                    }

                    $('#modalVerCliente').modal('show');
                },
                error: function () {
                    alert('Error al cargar el cliente');
                }
            });
        });

        $('#modalVerCliente').on('hidden.bs.modal', function () {
            $('#verClienteFoto').attr('src', '').addClass('d-none');
            $('#verClienteFotoEmpty').removeClass('d-none');
        });
    });
})();
