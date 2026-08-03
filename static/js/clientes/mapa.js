// Configuración de URL de puntos (Django la inyecta en un atributo data-url del div del mapa)
var CLIENTES_MAPA_PUNTOS_URL = null;

(function () {
  function setInfo(text) {
    var el = document.getElementById('mapaClientesInfo');
    if (el) el.textContent = text || '';
  }

  function normText(v) {
    return (v || '').toString().trim().toLowerCase();
  }

  function safeText(v) {
    return (v || '').toString();
  }

  function el(id) { return document.getElementById(id); }

  function setHidden(node, hidden) {
    if (!node) return;
    if (hidden) node.setAttribute('hidden', '');
    else node.removeAttribute('hidden');
  }

  function escapeHtml(str) {
    return safeText(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function getFiltrosMapa() {
    var q = el('buscarClienteMapa')?.value || '';
    var estado = el('estadoClienteMapa')?.value || '';
    var vendedor = el('vendedorClienteMapa')?.value || '';
    return { q: q, estado: estado, vendedor: vendedor };
  }

  function buildUrlWithParams(baseUrl, params) {
    var url = new URL(baseUrl, window.location.origin);
    Object.keys(params).forEach(function (k) {
      if (params[k]) url.searchParams.set(k, params[k]);
    });
    return url.toString();
  }

  var allPuntos = [];
  var markers = [];
  var map, userMarker = null, userAccuracyCircle = null, userLocationLayer = null, userLocationWatchId = null, userLocationCentered = false;

  function buildGoogleMapsUrl(lat, lng) {
    return 'https://www.google.com/maps?q=' + encodeURIComponent(lat + ',' + lng);
  }

  function showBottom(p) {
    var bottom = el('clientesBottom');
    var titulo = el('clientesTitulo');
    var direccion = el('clientesDireccion');
    var meta = el('clientesMeta');
    var foto = el('clientesFoto');
    var fotoEmpty = el('clientesFotoEmpty');
    var btnMaps = el('btnAbrirGoogleMaps');
    if (!bottom || !titulo || !direccion || !meta) return;

    titulo.textContent = safeText(p.nombre || 'Cliente');
    direccion.textContent = safeText(p.direccion || '');

    var metaArr = [];
    if (p.telefono) metaArr.push('Tel: ' + safeText(p.telefono));
    if (p.ci_nit) metaArr.push('CI/NIT: ' + safeText(p.ci_nit));
    meta.textContent = metaArr.join(' • ');

    if (btnMaps) {
      if (typeof p.lat === 'number' && typeof p.lng === 'number') {
        btnMaps.href = buildGoogleMapsUrl(p.lat, p.lng);
        btnMaps.style.display = 'inline-flex';
      } else {
        btnMaps.removeAttribute('href');
        btnMaps.style.display = 'none';
      }
    }

    if (foto && fotoEmpty) {
      var url = safeText(p.foto_url || '');
      if (url) {
        foto.src = url;
        foto.style.display = 'block';
        fotoEmpty.style.display = 'none';
      } else {
        foto.removeAttribute('src');
        foto.style.display = 'none';
        fotoEmpty.style.display = 'flex';
      }
    }

    setHidden(bottom, false);
  }

  function hideBottom() { setHidden(el('clientesBottom'), true); }

  function openImageViewer(url) {
    var imgViewer = el('imgViewer');
    var img = el('imgViewerImg');
    if (!imgViewer || !img) return;
    if (!url) return;
    img.src = url;
    setHidden(imgViewer, false);
  }

  function closeImageViewer() { var imgViewer = el('imgViewer'); var img = el('imgViewerImg'); if (!imgViewer||!img) return; setHidden(imgViewer, true); img.removeAttribute('src'); }

  function updateUserLocationMarker(lat, lng, accuracy) {
    var latLng = [lat, lng];
    var radius = Math.max(Math.min((accuracy || 20), 25), 8);

    if (!userMarker) {
      userMarker = L.circleMarker(latLng, {
        radius: 8,
        fillColor: '#2563eb',
        color: '#ffffff',
        weight: 3,
        opacity: 1,
        fillOpacity: 0.95,
        zIndexOffset: 1000
      }).addTo(userLocationLayer);
      userMarker.bindTooltip('Tu ubicación');
      userMarker.bindPopup(
        '<div style="min-width: 180px;">' +
          '<div style="font-weight: 600; margin-bottom: 6px;">Tu ubicación</div>' +
          '<a href="' + buildGoogleMapsUrl(lat, lng) + '" target="_blank" rel="noopener" style="display: inline-block; padding: 6px 10px; background: #2563eb; color: #fff; border-radius: 6px; text-decoration: none; font-size: 12px;">Abrir en Google Maps</a>' +
        '</div>',
        { autoPan: true, maxWidth: 220 }
      );
    } else {
      userMarker.setLatLng(latLng);
      userMarker.setPopupContent(
        '<div style="min-width: 180px;">' +
          '<div style="font-weight: 600; margin-bottom: 6px;">Tu ubicación</div>' +
          '<a href="' + buildGoogleMapsUrl(lat, lng) + '" target="_blank" rel="noopener" style="display: inline-block; padding: 6px 10px; background: #2563eb; color: #fff; border-radius: 6px; text-decoration: none; font-size: 12px;">Abrir en Google Maps</a>' +
        '</div>'
      );
    }

    if (!userAccuracyCircle) {
      userAccuracyCircle = L.circle(latLng, {
        radius: radius,
        fillColor: '#60a5fa',
        color: '#60a5fa',
        weight: 1,
        opacity: 0.2,
        fillOpacity: 0.08,
        zIndexOffset: 999,
        interactive: false
      }).addTo(userLocationLayer);
    } else {
      userAccuracyCircle.setLatLng(latLng);
      userAccuracyCircle.setRadius(radius);
    }

    if (!userLocationCentered) {
      map.setView(latLng, 15);
      userLocationCentered = true;
    }
  }

  function startUserLocationTracking() {
    if (!navigator.geolocation) {
      setInfo('Tu navegador no admite geolocalización.');
      return;
    }
    if (userLocationWatchId !== null) return;
    userLocationWatchId = navigator.geolocation.watchPosition(function (pos) {
      updateUserLocationMarker(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy);
    }, function () {
      setInfo('No se pudo obtener tu ubicación. Permite el acceso a la ubicación del navegador.');
    }, { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 });
  }

  function cargarPuntos() {
    var url = CLIENTES_MAPA_PUNTOS_URL;
    if (!url) { setInfo('No se configuró la URL de puntos.'); return; }
    setInfo('Cargando clientes...');
    var params = getFiltrosMapa();
    fetch(buildUrlWithParams(url, params), { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (data) {
        allPuntos = (data && data.puntos) ? data.puntos : [];
        markers.forEach(function (m) { try { map.removeLayer(m); } catch (e) {} });
        markers = [];
        if (!allPuntos.length) { setInfo('No hay clientes con ubicación registrada.'); return; }
        var bounds = [];
        allPuntos.forEach(function (p) {
          if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return;
          var nombreCliente = p.nombre || 'Cliente';
          var popup = '<strong>' + escapeHtml(p.nombre || 'Cliente') + '</strong>';
          if (p.ci_nit) popup += '<br><small>CI/NIT: ' + escapeHtml(p.ci_nit) + '</small>';
          if (p.telefono) popup += '<br><small>Tel: ' + escapeHtml(p.telefono) + '</small>';
          if (p.direccion) popup += '<br><small>' + escapeHtml(p.direccion) + '</small>';
          var marker = L.marker([p.lat, p.lng]).addTo(map).bindTooltip(nombreCliente, { permanent: true, direction: 'top', offset: [0, -8], className: 'mapa-cliente-label' }).bindPopup(popup);
          marker.on('click', function () { showBottom(p); });
          markers.push(marker);
          bounds.push([p.lat, p.lng]);
        });
        if (bounds.length) map.fitBounds(bounds, { padding: [24, 24] });
        setInfo('Mostrando ' + allPuntos.length + ' cliente(s) en el mapa.');
      })
      .catch(function () { setInfo('No se pudo cargar el mapa de clientes.'); });
  }

  function init() {
    var mapEl = el('mapaClientes'); if (!mapEl) return;
    CLIENTES_MAPA_PUNTOS_URL = mapEl.getAttribute('data-url');
    map = L.map('mapaClientes', { zoomControl: true });
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', { subdomains: 'abcd', maxZoom: 19, attribution: '&copy; OpenStreetMap &copy; CARTO' }).addTo(map);
    map.setView([-17.7833, -63.1821], 12);

    userLocationLayer = L.layerGroup().addTo(map);

    cargarPuntos();

    var inputBuscar = el('buscarClienteMapa');
    var selectEstado = el('estadoClienteMapa');
    var selectVendedor = el('vendedorClienteMapa');
    [inputBuscar, selectEstado, selectVendedor].forEach(function (node) { if (node) node.addEventListener('input', function () { cargarPuntos(); }); });

    var btn = el('btnClientesFiltro'); var filtros = el('clientesFiltros'); if (btn && filtros) btn.addEventListener('click', function () { filtros.hidden = !filtros.hidden; });

    var btnMiUbic = el('btnMiUbicacion'); if (btnMiUbic) {
      btnMiUbic.addEventListener('click', function () {
        if (userMarker && userAccuracyCircle) { map.setView(userMarker.getLatLng(), Math.max(map.getZoom(), 15)); return; }
        startUserLocationTracking();
      });
    }

    // Click en foto para ampliar
    var fotoWrap = el('clientesFotoWrap'); if (fotoWrap) { fotoWrap.addEventListener('click', function () { var f = el('clientesFoto'); if (f) { var src = f.getAttribute('src'); if (src) openImageViewer(src); } }); }

    var imgViewerClose = el('imgViewerClose'); if (imgViewerClose) imgViewerClose.addEventListener('click', function () { closeImageViewer(); });
    var imgViewer = el('imgViewer'); if (imgViewer) imgViewer.addEventListener('click', function (e) { if (e.target === imgViewer) closeImageViewer(); });

    var btnCerrar = el('clientesCerrar'); if (btnCerrar) btnCerrar.addEventListener('click', function () { hideBottom(); });

    // Delegación: clic en label del tooltip para mostrar tarjeta
    document.addEventListener('click', function (e) {
      var t = e.target; if (!t) return; var label = (t.closest) ? t.closest('.mapa-label') : null; if (!label) return; var pid = label.getAttribute('data-pedido-id'); if (!pid) return;
      // buscar punto por id (aquí clientes usan id)
      var id = label.getAttribute('data-cliente-id') || pid;
      for (var i = 0; i < allPuntos.length; i++) { if (String(allPuntos[i].id) === String(id)) { showBottom(allPuntos[i]); break; } }
    });

    // cerrar visor con Esc
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closeImageViewer(); hideBottom(); } });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
