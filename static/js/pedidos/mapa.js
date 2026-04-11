(function () {
  function setInfo(text) {
    var el = document.getElementById('mapaPedidosInfo');
    if (el) el.textContent = text || '';
  }

  function init() {
    var mapEl = document.getElementById('mapaPedidos');
    if (!mapEl) return;

    var map = L.map('mapaPedidos', { zoomControl: true });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      subdomains: 'abcd',
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap &copy; CARTO',
    }).addTo(map);

    map.setView([-17.7833, -63.1821], 12);

    var url = window.PEDIDOS_MAPA_PUNTOS_URL;
    if (!url) {
      setInfo('No se configuró la URL de puntos.');
      return;
    }

    setInfo('Cargando pedidos pendientes...');

    var styles = getComputedStyle(document.documentElement);
    var colorAdvertencia = (styles.getPropertyValue('--color-advertencia') || '').trim();
    if (!colorAdvertencia) colorAdvertencia = 'var(--color-advertencia)';

    fetch(url, {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var puntos = (data && data.puntos) ? data.puntos : [];
        if (!puntos.length) {
          setInfo('No hay pedidos pendientes con ubicación registrada.');
          return;
        }

        var bounds = [];

        puntos.forEach(function (p) {
          if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return;

          var popup = '<strong>Pedido #' + (p.pedido_id || '') + '</strong>';
          if (p.cliente) popup += '<br><small><b>Cliente:</b> ' + p.cliente + '</small>';
          if (p.ci_nit) popup += '<br><small>CI/NIT: ' + p.ci_nit + '</small>';
          if (p.telefono) popup += '<br><small>Tel: ' + p.telefono + '</small>';
          if (p.direccion) popup += '<br><small>' + p.direccion + '</small>';
          if (p.fecha) popup += '<br><small><b>Fecha:</b> ' + p.fecha + '</small>';
          if (p.total) popup += '<br><small><b>Total:</b> ' + p.total + '</small>';

          // Marcador amarillo (circleMarker para no depender de iconos externos)
          L.circleMarker([p.lat, p.lng], {
            radius: 8,
            color: colorAdvertencia,
            weight: 2,
            fillColor: colorAdvertencia,
            fillOpacity: 0.9,
          }).addTo(map).bindPopup(popup);

          bounds.push([p.lat, p.lng]);
        });

        if (bounds.length) {
          map.fitBounds(bounds, { padding: [24, 24] });
        }

        setInfo('Mostrando ' + puntos.length + ' pedido(s) pendiente(s) en el mapa.');
      })
      .catch(function () {
        setInfo('No se pudo cargar el mapa de pedidos.');
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
