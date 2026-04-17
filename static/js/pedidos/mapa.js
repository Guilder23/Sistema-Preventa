(function () {
  function setInfo(text) {
    var el = document.getElementById('mapaPedidosInfo');
    if (el) el.textContent = text || '';
  }

  function normText(v) {
    return (v || '').toString().trim().toLowerCase();
  }

  function safeText(v) {
    return (v || '').toString();
  }

  function el(id) {
    return document.getElementById(id);
  }

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

    var searchInput = el('repartidorBuscar');
    var searchWrap = el('repartidorSearchWrap');
    var filtrosWrap = el('repartidorFiltros');
    var estadoSelect = el('repartidorEstado');
    var btnFiltro = el('btnRepartidorFiltro');

    var bottom = el('repartidorBottom');
    var bottomTitulo = el('repartidorTitulo');
    var bottomDireccion = el('repartidorDireccion');
    var bottomMeta = el('repartidorMeta');
    var bottomFoto = el('repartidorFoto');
    var bottomFotoEmpty = el('repartidorFotoEmpty');
    var btnCerrar = el('repartidorCerrar');

    var imgViewer = el('imgViewer');
    var imgViewerImg = el('imgViewerImg');
    var imgViewerClose = el('imgViewerClose');

    function toggleFiltros() {
      if (!filtrosWrap) return;
      var isHidden = filtrosWrap.hasAttribute('hidden');
      setHidden(filtrosWrap, !isHidden);
    }

    // Buscador siempre visible (sin colapsar)

    if (btnFiltro) {
      btnFiltro.addEventListener('click', function () {
        toggleFiltros();
      });
    }

    if (searchWrap) {
      // si se toca el contenedor del buscador, enfoca el input
      searchWrap.addEventListener('click', function () {
        if (searchInput) searchInput.focus();
      });
    }

    function hideBottom() {
      setHidden(bottom, true);
    }

    function openImageViewer(url) {
      if (!imgViewer || !imgViewerImg) return;
      if (!url) return;
      imgViewerImg.src = url;
      setHidden(imgViewer, false);
    }

    function closeImageViewer() {
      if (!imgViewer || !imgViewerImg) return;
      setHidden(imgViewer, true);
      imgViewerImg.removeAttribute('src');
    }

    if (imgViewerClose) {
      imgViewerClose.addEventListener('click', function () {
        closeImageViewer();
      });
    }
    if (imgViewer) {
      imgViewer.addEventListener('click', function (e) {
        // cerrar tocando el fondo (pero no la imagen)
        if (e.target === imgViewer) closeImageViewer();
      });
    }

    if (btnCerrar) {
      btnCerrar.addEventListener('click', function () {
        hideBottom();
      });
    }

    var layerGroup = L.layerGroup().addTo(map);
    var markersByPedido = Object.create(null);
    var allPuntos = [];
    var selectedPedidoId = null;

    function markerColorByEstado(estado) {
      if (estado === 'vendido') return '#28a745';
      if (estado === 'anulado') return '#dc3545';
      if (estado === 'no_entregado') return '#6c757d';
      return '#ffc107';
    }

    function buildPopupHtml(p) {
      var popup = '<strong>Pedido #' + escapeHtml(p.pedido_id || '') + '</strong>';
      if (p.cliente) popup += '<br><small><b>Cliente:</b> ' + escapeHtml(p.cliente) + '</small>';
      if (p.estado_str) popup += '<br><small><b>Estado:</b> ' + escapeHtml(p.estado_str) + '</small>';
      if (p.ci_nit) popup += '<br><small>CI/NIT: ' + escapeHtml(p.ci_nit) + '</small>';
      if (p.telefono) popup += '<br><small>Tel: ' + escapeHtml(p.telefono) + '</small>';
      if (p.direccion) popup += '<br><small>' + escapeHtml(p.direccion) + '</small>';
      if (p.fecha) popup += '<br><small><b>Fecha:</b> ' + escapeHtml(p.fecha) + '</small>';
      if (p.total) popup += '<br><small><b>Total:</b> Bs ' + escapeHtml(p.total) + '</small>';
      return popup;
    }

    function showBottom(p) {
      if (!bottom || !bottomTitulo || !bottomDireccion || !bottomMeta) return;

      bottomTitulo.textContent = safeText(p.cliente || ('Pedido #' + (p.pedido_id || '')));
      bottomDireccion.textContent = safeText(p.direccion || '');

      var meta = [];
      if (p.estado_str) meta.push('Estado: ' + safeText(p.estado_str));
      if (p.telefono) meta.push('Tel: ' + safeText(p.telefono));
      if (p.total) meta.push('Total: Bs ' + safeText(p.total));
      bottomMeta.textContent = meta.join(' • ');

      if (bottomFoto && bottomFotoEmpty) {
        var url = safeText(p.foto_url || '');
        if (url) {
          bottomFoto.src = url;
          bottomFoto.style.display = 'block';
          bottomFotoEmpty.style.display = 'none';
        } else {
          bottomFoto.removeAttribute('src');
          bottomFoto.style.display = 'none';
          bottomFotoEmpty.style.display = 'flex';
        }
      }

      setHidden(bottom, false);
    }

    function matchesFilters(p) {
      var q = normText(searchInput && searchInput.value);
      var estado = (estadoSelect && estadoSelect.value) ? estadoSelect.value : '';

      if (estado && normText(p.estado) !== estado) return false;

      if (!q) return true;

      var hay = [
        p.cliente,
        p.ci_nit,
        p.telefono,
        p.direccion,
        p.estado_str,
      ].map(normText).join(' ');

      return hay.indexOf(q) !== -1;
    }

    function selectPedido(pedidoId) {
      selectedPedidoId = pedidoId;
      var p = null;
      for (var i = 0; i < allPuntos.length; i++) {
        if (String(allPuntos[i].pedido_id) === String(pedidoId)) {
          p = allPuntos[i];
          break;
        }
      }
      if (!p) {
        hideBottom();
        return;
      }
      showBottom(p);
    }

    function render() {
      layerGroup.clearLayers();
      markersByPedido = Object.create(null);

      var bounds = [];
      var visibles = 0;

      allPuntos.forEach(function (p) {
        if (typeof p.lat !== 'number' || typeof p.lng !== 'number') return;
        if (!matchesFilters(p)) return;

        visibles += 1;
        var nombreCliente = p.cliente || 'Cliente';
        var color = markerColorByEstado(normText(p.estado));

        var marker = L.circleMarker([p.lat, p.lng], {
          radius: 9,
          fillColor: color,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9
        })
          .addTo(layerGroup)
          .bindTooltip(
            '<span class="mapa-label" data-pedido-id="' + escapeHtml(p.pedido_id) + '">' + escapeHtml(nombreCliente) + '</span>',
            {
            permanent: true,
            direction: 'top',
            offset: [0, -12],
            className: 'mapa-cliente-label'
            }
          )
          .bindPopup(buildPopupHtml(p));

        marker.on('click', function () {
          selectPedido(p.pedido_id);
        });

        markersByPedido[String(p.pedido_id)] = marker;
        bounds.push([p.lat, p.lng]);
      });

      if (bounds.length) {
        map.fitBounds(bounds, { padding: [24, 24] });
      }

      // Si la selección ya no está visible, cerramos la tarjeta.
      if (selectedPedidoId != null) {
        var stillVisible = false;
        for (var k = 0; k < allPuntos.length; k++) {
          if (String(allPuntos[k].pedido_id) === String(selectedPedidoId) && matchesFilters(allPuntos[k])) {
            stillVisible = true;
            break;
          }
        }
        if (!stillVisible) hideBottom();
      }

      if (visibles === 0) {
        setInfo('No hay pedidos que coincidan con los filtros.');
      } else {
        setInfo('Mostrando ' + visibles + ' pedido(s) en el mapa.');
      }
    }

    function wireFilters() {
      if (searchInput) {
        searchInput.addEventListener('input', function () {
          render();
        });
      }
      if (estadoSelect) {
        estadoSelect.addEventListener('change', function () {
          render();
        });
      }
    }

    wireFilters();

    // Clic sobre el nombre (tooltip) => muestra la tarjeta (delegación global)
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (!t) return;
      var label = (t.closest) ? t.closest('.mapa-label') : null;
      if (!label) return;
      var pid = label.getAttribute('data-pedido-id');
      if (pid) selectPedido(pid);
    });

    // Clic en foto => ampliar
    var fotoWrap = el('repartidorFotoWrap');
    if (fotoWrap) {
      fotoWrap.addEventListener('click', function () {
        if (!bottomFoto) return;
        var src = bottomFoto.getAttribute('src');
        if (src) openImageViewer(src);
      });
    }

    fetch(url, {
      credentials: 'same-origin',
      headers: { 'Accept': 'application/json' },
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        allPuntos = (data && data.puntos) ? data.puntos : [];
        if (!allPuntos.length) {
          setInfo('No hay pedidos pendientes con ubicación registrada.');
          return;
        }

        render();
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
