(function () {
    'use strict';

    function setEstado(el, text) {
        if (el) el.textContent = text;
    }

    function capturarUbicacion(latInput, lonInput, estadoEl) {
        if (!navigator.geolocation) {
            setEstado(estadoEl, 'Geolocalización no soportada');
            return;
        }
        setEstado(estadoEl, 'Obteniendo ubicación...');
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                latInput.value = lat;
                lonInput.value = lon;
                setEstado(estadoEl, `OK: ${lat.toFixed(5)}, ${lon.toFixed(5)}`);
            },
            () => {
                setEstado(estadoEl, 'No se pudo obtener ubicación');
            },
            { enableHighAccuracy: true, timeout: 8000 }
        );
    }

    $(document).ready(function () {
        let camaraEditar = null;
        if (typeof window.initClienteFotoCamara === 'function') {
            camaraEditar = window.initClienteFotoCamara({
                fileInputId: 'editFotoTienda',
                previewId: 'editFotoTiendaPreview',
                btnAbrirId: 'btnEditFotoCamara',
                wrapId: 'editCamaraWrap',
                videoId: 'editCamaraVideo',
                btnCapturarId: 'btnEditCamaraCapturar',
                btnCerrarId: 'btnEditCamaraCerrar'
            });
        }

        const btnSeleccionar = document.getElementById('btnEditFotoSeleccionar');
        const fotoNombre = document.getElementById('editFotoTiendaNombre');

        $(document).on('click', '.btn-editar-cliente', function (e) {
            e.preventDefault();
            const id = $(this).data('cliente-id');
            if (!id) return;

            $.ajax({
                url: `/clientes/${id}/obtener/`,
                type: 'GET',
                dataType: 'json',
                success: function (data) {
                    $('#editClienteId').val(data.id);
                    $('#editNombres').val(data.nombres);
                    $('#editApellidos').val(data.apellidos || '');
                    $('#editCiNit').val(data.ci_nit || '');
                    $('#editTelefono').val(data.telefono || '');
                    $('#editDireccion').val(data.direccion || '');
                    $('#editDescripcion').val(data.descripcion || '');
                    $('#editLatitud').val(data.latitud || '');
                    $('#editLongitud').val(data.longitud || '');
                    $('#editActivoCliente').prop('checked', !!data.activo);

                    const fotoPreview = document.getElementById('editFotoTiendaPreview');
                    if (fotoPreview) {
                        if (data.foto_url) {
                            fotoPreview.src = data.foto_url;
                            fotoPreview.classList.remove('d-none');
                        } else {
                            fotoPreview.src = '';
                            fotoPreview.classList.add('d-none');
                        }
                    }

                    const st = document.getElementById('ubicacionEditarEstado');
                    if (data.latitud && data.longitud) {
                        setEstado(st, `Actual: ${parseFloat(data.latitud).toFixed(5)}, ${parseFloat(data.longitud).toFixed(5)}`);
                    } else {
                        setEstado(st, 'Sin ubicación');
                    }

                    $('#modalEditarCliente').modal('show');
                },
                error: function () {
                    alert('Error al cargar el cliente');
                }
            });
        });

        document.getElementById('btnUbicacionEditar')?.addEventListener('click', function () {
            capturarUbicacion(
                document.getElementById('editLatitud'),
                document.getElementById('editLongitud'),
                document.getElementById('ubicacionEditarEstado')
            );
        });

        const fotoInput = document.getElementById('editFotoTienda');
        const fotoPreview = document.getElementById('editFotoTiendaPreview');

        if (btnSeleccionar && fotoInput) {
            btnSeleccionar.addEventListener('click', function () {
                fotoInput.click();
            });
        }

        if (fotoInput && fotoPreview) {
            fotoInput.addEventListener('change', function () {
                const file = fotoInput.files && fotoInput.files[0];
                if (fotoNombre) {
                    fotoNombre.textContent = file ? file.name : 'Ningún archivo seleccionado';
                }
                if (!file) {
                    fotoPreview.src = '';
                    fotoPreview.classList.add('d-none');
                    return;
                }
                const url = URL.createObjectURL(file);
                fotoPreview.src = url;
                fotoPreview.classList.remove('d-none');
            });
        }

        $('#formEditarCliente').on('submit', function (e) {
            const id = $('#editClienteId').val();
            if (!id) {
                e.preventDefault();
                return false;
            }
            $(this).attr('action', `/clientes/${id}/editar/`);
        });

        $('#modalEditarCliente').on('hidden.bs.modal', function () {
            if (camaraEditar) {
                camaraEditar.stop();
            }
            $('#formEditarCliente')[0].reset();
            setEstado(document.getElementById('ubicacionEditarEstado'), 'Sin ubicación');

            const fp = document.getElementById('editFotoTiendaPreview');
            const fi = document.getElementById('editFotoTienda');
            if (fp) {
                fp.src = '';
                fp.classList.add('d-none');
            }
            if (fi) fi.value = '';

            if (fotoNombre) {
                fotoNombre.textContent = 'Ningún archivo seleccionado';
            }
        });
    });
})();
