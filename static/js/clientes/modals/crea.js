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
        const btn = document.getElementById('btnUbicacionCrear');
        if (!btn) return;
        btn.addEventListener('click', function () {
            capturarUbicacion(
                document.getElementById('crearLatitud'),
                document.getElementById('crearLongitud'),
                document.getElementById('ubicacionCrearEstado')
            );
        });

        $('#modalCrearCliente').on('hidden.bs.modal', function () {
            const lat = document.getElementById('crearLatitud');
            const lon = document.getElementById('crearLongitud');
            const st = document.getElementById('ubicacionCrearEstado');
            if (lat) lat.value = '';
            if (lon) lon.value = '';
            setEstado(st, 'Sin ubicación');
        });
    });
})();
