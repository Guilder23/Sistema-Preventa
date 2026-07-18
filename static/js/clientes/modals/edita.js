(function () {
    'use strict';

    function setEstado(el, text) {
        if (el) el.textContent = text;
    }

    function formatearTextoUbicacion(lat, lon) {
        if (lat === '' || lon === '' || lat === null || lon === null) return 'Sin ubicación';
        return `Lat ${parseFloat(lat).toFixed(5)} · Lon ${parseFloat(lon).toFixed(5)}`;
    }

    function actualizarTextoUbicacion(latInput, lonInput, textoEl) {
        if (textoEl) {
            textoEl.textContent = formatearTextoUbicacion(latInput.value, lonInput.value);
        }
    }

    function initMapaUbicacion(mapId, latInput, lonInput, textoEl, editBtnId, estadoEl) {
        const mapEl = document.getElementById(mapId);
        const editBtn = document.getElementById(editBtnId);
        if (!mapEl || typeof window.L === 'undefined') return null;

        const map = window.L.map(mapEl, {
            zoomControl: true,
            scrollWheelZoom: true,
            attributionControl: true
        });
        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        let marker = null;
        let editable = false;

        function establecerMarcador(lat, lon) {
            const latNum = parseFloat(lat);
            const lonNum = parseFloat(lon);
            if (!Number.isFinite(latNum) || !Number.isFinite(lonNum)) return;
            if (!marker) {
                marker = window.L.marker([latNum, lonNum], { draggable: true }).addTo(map);
                marker.on('dragend', function (evt) {
                    if (!editable) return;
                    const point = evt.target.getLatLng();
                    latInput.value = point.lat.toFixed(7);
                    lonInput.value = point.lng.toFixed(7);
                    actualizarTextoUbicacion(latInput, lonInput, textoEl);
                });
            } else {
                marker.setLatLng([latNum, lonNum]);
            }
            map.setView([latNum, lonNum], 16);
            if (marker && marker.dragging) {
                marker.dragging[editable ? 'enable' : 'disable']();
            }
        }

        function syncDesdeInputs() {
            actualizarTextoUbicacion(latInput, lonInput, textoEl);
            if (!editable) {
                establecerMarcador(latInput.value, lonInput.value);
            }
        }

        function refrescarMapa() {
            if (map && map.invalidateSize) {
                window.setTimeout(function () {
                    map.invalidateSize();
                    if (marker) {
                        const latLng = marker.getLatLng();
                        if (latLng) {
                            map.setView([latLng.lat, latLng.lng], Math.max(map.getZoom(), 15));
                        }
                    }
                }, 120);
            }
        }

        if (editBtn) {
            editBtn.addEventListener('click', function () {
                editable = !editable;
                editBtn.classList.toggle('btn-primary', editable);
                editBtn.classList.toggle('btn-outline-secondary', !editable);
                editBtn.innerHTML = editable
                    ? '<i class="fas fa-map-marker-alt"></i> Mover marcador'
                    : '<i class="fas fa-map-marker-alt"></i> Editar mapa';
                if (marker && marker.dragging) {
                    marker.dragging[editable ? 'enable' : 'disable']();
                }
                if (estadoEl) {
                    setEstado(estadoEl, editable ? 'Modo edición activado' : 'Modo edición desactivado');
                }
                refrescarMapa();
            });
        }

        [latInput, lonInput].forEach(function (input) {
            input.addEventListener('input', function () {
                syncDesdeInputs();
            });
        });

        syncDesdeInputs();
        refrescarMapa();
        window.setTimeout(refrescarMapa, 250);
        window.setTimeout(refrescarMapa, 600);
        return {
            map: map,
            setPosition: function (lat, lon) {
                latInput.value = parseFloat(lat).toFixed(7);
                lonInput.value = parseFloat(lon).toFixed(7);
                actualizarTextoUbicacion(latInput, lonInput, textoEl);
                establecerMarcador(latInput.value, lonInput.value);
                refrescarMapa();
            }
        };
    }

    function capturarUbicacion(latInput, lonInput, estadoEl, textoEl, mapId, editBtnId) {
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
                actualizarTextoUbicacion(latInput, lonInput, textoEl);
                if (typeof window.L !== 'undefined') {
                    const mapObj = window.__clienteUbicacionMapaEditar;
                    if (mapObj && mapObj.setPosition) {
                        mapObj.setPosition(lat, lon);
                    }
                }
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
                    actualizarTextoUbicacion(document.getElementById('editLatitud'), document.getElementById('editLongitud'), document.getElementById('ubicacionTextoEditar'));
                    if (window.__clienteUbicacionMapaEditar && window.__clienteUbicacionMapaEditar.setPosition && data.latitud && data.longitud) {
                        window.__clienteUbicacionMapaEditar.setPosition(data.latitud, data.longitud);
                    }

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

                    $('#modalEditarCliente').on('shown.bs.modal', function () {
                        if (window.__clienteUbicacionMapaEditar && window.__clienteUbicacionMapaEditar.map && window.__clienteUbicacionMapaEditar.map.invalidateSize) {
                            window.__clienteUbicacionMapaEditar.map.invalidateSize();
                        }
                    });
                    $('#modalEditarCliente').modal('show');
                },
                error: function () {
                    alert('Error al cargar el cliente');
                }
            });
        });

        const latInputEditar = document.getElementById('editLatitud');
        const lonInputEditar = document.getElementById('editLongitud');
        const textoUbicacionEditar = document.getElementById('ubicacionTextoEditar');
        const mapaEditar = initMapaUbicacion('mapaUbicacionEditar', latInputEditar, lonInputEditar, textoUbicacionEditar, 'btnEditarMapaEditar', document.getElementById('ubicacionEditarEstado'));
        window.__clienteUbicacionMapaEditar = mapaEditar;

        document.getElementById('btnUbicacionEditar')?.addEventListener('click', function () {
            capturarUbicacion(
                latInputEditar,
                lonInputEditar,
                document.getElementById('ubicacionEditarEstado'),
                textoUbicacionEditar,
                'mapaUbicacionEditar',
                'btnEditarMapaEditar'
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
            const texto = document.getElementById('ubicacionTextoEditar');
            if (texto) texto.textContent = 'Sin ubicación';

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
