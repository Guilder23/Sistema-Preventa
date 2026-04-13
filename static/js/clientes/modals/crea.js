(function (global) {
    'use strict';

    function stopStream(state) {
        if (state.stream) {
            state.stream.getTracks().forEach(function (t) {
                t.stop();
            });
            state.stream = null;
        }
        if (state.video) {
            state.video.srcObject = null;
        }
    }

    function openUserMedia() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            return Promise.reject(new Error('no-getUserMedia'));
        }
        var withFacing = { video: { facingMode: { ideal: 'environment' } }, audio: false };
        return navigator.mediaDevices.getUserMedia(withFacing).catch(function () {
            return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        });
    }

    function blobToFile(blob) {
        var name = 'tienda_camara_' + Date.now() + '.jpg';
        try {
            return new File([blob], name, { type: 'image/jpeg' });
        } catch (e) {
            blob.name = name;
            return blob;
        }
    }

    /**
     * Tomar foto con la cámara y asignarla al input file (mismo envío que galería).
     */
    function initClienteFotoCamara(options) {
        var fileInput = document.getElementById(options.fileInputId);
        var preview = document.getElementById(options.previewId);
        var btnAbrir = document.getElementById(options.btnAbrirId);
        var wrap = document.getElementById(options.wrapId);
        var video = document.getElementById(options.videoId);
        var btnCapturar = document.getElementById(options.btnCapturarId);
        var btnCerrar = document.getElementById(options.btnCerrarId);
        if (!fileInput || !preview || !btnAbrir || !wrap || !video || !btnCapturar || !btnCerrar) {
            return null;
        }

        var state = { stream: null, video: video };

        function cerrarCamara() {
            stopStream(state);
            wrap.classList.add('d-none');
        }

        btnAbrir.addEventListener('click', function () {
            if (!window.isSecureContext) {
                alert(
                    'La cámara solo funciona en HTTPS. Esta página no es un contexto seguro (revisa la URL).'
                );
                return;
            }
            openUserMedia()
                .then(function (stream) {
                    state.stream = stream;
                    video.srcObject = stream;
                    wrap.classList.remove('d-none');
                })
                .catch(function () {
                    alert(
                        'No se pudo acceder a la cámara. Permite el permiso del sitio en el navegador o prueba otro navegador.'
                    );
                });
        });

        btnCapturar.addEventListener('click', function () {
            if (!state.stream || !video.videoWidth) {
                return;
            }
            var canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            var ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            canvas.toBlob(
                function (blob) {
                    if (!blob) {
                        return;
                    }
                    var file = blobToFile(blob);
                    var dt = new DataTransfer();
                    try {
                        dt.items.add(file);
                        fileInput.files = dt.files;
                    } catch (e) {
                        alert('Tu navegador no permite asignar la foto al formulario. Elige imagen desde archivos.');
                        return;
                    }
                    if (preview.src && preview.src.indexOf('blob:') === 0) {
                        URL.revokeObjectURL(preview.src);
                    }
                    preview.src = URL.createObjectURL(file);
                    preview.classList.remove('d-none');
                    cerrarCamara();
                    fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                },
                'image/jpeg',
                0.92
            );
        });

        btnCerrar.addEventListener('click', cerrarCamara);

        return {
            stop: cerrarCamara
        };
    }

    global.initClienteFotoCamara = initClienteFotoCamara;
})(window);

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

    document.addEventListener('DOMContentLoaded', function () {
        let camaraCrear = null;
        if (typeof window.initClienteFotoCamara === 'function') {
            camaraCrear = window.initClienteFotoCamara({
                fileInputId: 'crearFotoTienda',
                previewId: 'crearFotoTiendaPreview',
                btnAbrirId: 'btnCrearFotoCamara',
                wrapId: 'crearCamaraWrap',
                videoId: 'crearCamaraVideo',
                btnCapturarId: 'btnCrearCamaraCapturar',
                btnCerrarId: 'btnCrearCamaraCerrar'
            });
        }

        const btnUbicacion = document.getElementById('btnUbicacionCrear');
        if (btnUbicacion) {
            btnUbicacion.addEventListener('click', function () {
                capturarUbicacion(
                    document.getElementById('crearLatitud'),
                    document.getElementById('crearLongitud'),
                    document.getElementById('ubicacionCrearEstado')
                );
            });
        }

        const fotoInput = document.getElementById('crearFotoTienda');
        const fotoPreview = document.getElementById('crearFotoTiendaPreview');
        const fotoNombre = document.getElementById('crearFotoTiendaNombre');
        const btnSeleccionar = document.getElementById('btnCrearFotoSeleccionar');

        if (btnSeleccionar && fotoInput) {
            btnSeleccionar.addEventListener('click', function () {
                fotoInput.click();
            });
        }

        if (fotoInput) {
            fotoInput.addEventListener('change', function () {
                const file = fotoInput.files && fotoInput.files[0];
                if (fotoNombre) {
                    fotoNombre.textContent = file ? file.name : 'Ningún archivo seleccionado';
                }

                if (!fotoPreview) return;
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

        $('#modalCrearCliente').on('hidden.bs.modal', function () {
            if (camaraCrear) {
                camaraCrear.stop();
            }
            const lat = document.getElementById('crearLatitud');
            const lon = document.getElementById('crearLongitud');
            const st = document.getElementById('ubicacionCrearEstado');
            if (lat) lat.value = '';
            if (lon) lon.value = '';
            setEstado(st, 'Sin ubicación');

            if (fotoInput && fotoPreview) {
                fotoInput.value = '';
                fotoPreview.src = '';
                fotoPreview.classList.add('d-none');
            }

            if (fotoNombre) {
                fotoNombre.textContent = 'Ningún archivo seleccionado';
            }
        });
    });
})();
