(function () {
  function setInfo(text) {
    var el = document.getElementById('mapaClientesInfo');
    if (el) el.textContent = text || '';
  }

  function init() {
    var mapEl = document.getElementById('mapaClientes');
    if (!mapEl) return;

    var map = L.map('mapaClientes', {
      zoomControl: true,
    });

    // Tile layer (evita bloqueo por políticas de referer del tile server de OSM)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    }).addTo(map);

    // Default center (lat/lng genérico) mientras cargamos puntos
    map.setView([-17.7833, -63.1821], 12);

    var url = window.CLIENTES_MAPA_PUNTOS_URL;
    if (!url) {
      setInfo('No se configuró la URL de puntos.');
      return;
    }

    setInfo('Cargando clientes...');

    fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
      },
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var puntos = (data && data.puntos) ? data.puntos : [];
        if (!puntos.length) {
          setInfo('No hay clientes con ubicación registrada.');
          return;
        }

        var bounds = [];
        puntos.forEach(function (p) {
          if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return;

          var popup = '<strong>' + (p.nombre || 'Cliente') + '</strong>';
          if (p.ci_nit) popup += '<br><small>CI/NIT: ' + p.ci_nit + '</small>';
          if (p.telefono) popup += '<br><small>Tel: ' + p.telefono + '</small>';
          if (p.direccion) popup += '<br><small>' + p.direccion + '</small>';

          L.marker([p.lat, p.lng]).addTo(map).bindPopup(popup);
          bounds.push([p.lat, p.lng]);
        });

        if (bounds.length) {
          map.fitBounds(bounds, { padding: [24, 24] });
        }

        setInfo('Mostrando ' + puntos.length + ' cliente(s) en el mapa.');
      })
      .catch(function () {
        setInfo('No se pudo cargar el mapa de clientes.');
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
