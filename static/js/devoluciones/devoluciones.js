(function () {
    'use strict';

    function getFilterValues() {
        return {
            q: (document.getElementById('q_devoluciones_lista')?.value || '').trim(),
            estado_reposicion: (document.getElementById('estado_reposicion')?.value || '').trim(),
            tipo: (document.getElementById('tipo')?.value || '').trim(),
            repartidor: (document.getElementById('repartidor')?.value || '').trim(),
            fecha_desde: (document.getElementById('fecha_desde')?.value || '').trim(),
            fecha_hasta: (document.getElementById('fecha_hasta')?.value || '').trim()
        };
    }

    function applyRealtimeFilters() {
        var values = getFilterValues();
        var url = new URL(window.location.href);

        Object.keys(values).forEach(function (k) {
            if (values[k]) {
                url.searchParams.set(k, values[k]);
            } else {
                url.searchParams.delete(k);
            }
        });

        // Guardar foco si estamos en el buscador
        var activeInput = document.activeElement;
        if (activeInput && activeInput.name === 'q') {
            sessionStorage.setItem('devolucionesSearchFocusId', activeInput.id);
        }

        window.location.href = url.toString();
    }

    // Restaurar foco con un pequeño retraso
    function restoreFocus() {
        var focusId = sessionStorage.getItem('devolucionesSearchFocusId');
        if (focusId) {
            setTimeout(function() {
                var qInput = document.getElementById(focusId);
                if (qInput) {
                    qInput.focus();
                    var val = qInput.value;
                    qInput.value = '';
                    qInput.value = val;
                }
                sessionStorage.removeItem('devolucionesSearchFocusId');
            }, 150);
        }
    }

    function renderResumen(bodyId, totalItemsId, totalAumentaId, resumen) {
        var body = document.getElementById(bodyId);
        if (!body) return;

        body.innerHTML = '';
        var productos = (resumen && resumen.productos) ? resumen.productos : [];
        var totalItems = (resumen && typeof resumen.total_items !== 'undefined') ? resumen.total_items : 0;
        var totalAumenta = (resumen && typeof resumen.total_aumenta !== 'undefined') ? resumen.total_aumenta : 0;

        var totalItemsNode = document.getElementById(totalItemsId);
        var totalAumentaNode = document.getElementById(totalAumentaId);
        if (totalItemsNode) totalItemsNode.textContent = totalItems;
        if (totalAumentaNode) totalAumentaNode.textContent = totalAumenta;

        if (!productos.length) {
            var trEmpty = document.createElement('tr');
            trEmpty.innerHTML = '<td colspan="4" class="text-center text-muted">No hay items pendientes para reponer</td>';
            body.appendChild(trEmpty);
            return;
        }

        productos.forEach(function (p) {
            var tr = document.createElement('tr');
            tr.innerHTML = [
                '<td>' + (p.producto || '-') + '</td>',
                '<td class="text-center">' + (p.stock_actual || 0) + '</td>',
                '<td class="text-center text-success font-weight-bold">+' + (p.aumenta || 0) + '</td>',
                '<td class="text-center font-weight-bold">' + (p.stock_final || 0) + '</td>'
            ].join('');
            body.appendChild(tr);
        });
    }

    function syncHiddenTodoInputs(values) {
        var map = ['q', 'estado_reposicion', 'tipo', 'repartidor', 'fecha_desde', 'fecha_hasta'];
        map.forEach(function (k) {
            var node = document.getElementById('todo_' + k);
            if (node) node.value = values[k] || '';
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var qInput = document.getElementById('q_devoluciones_lista');
        var estadoSelect = document.getElementById('estado_reposicion');
        var tipoSelect = document.getElementById('tipo');
        var repartidorSelect = document.getElementById('repartidor');
        var fechaDesde = document.getElementById('fecha_desde');
        var fechaHasta = document.getElementById('fecha_hasta');
        var debounceTimer;

        // Restaurar foco
        restoreFocus();

        if (qInput) {
            qInput.addEventListener('input', function () {
                window.clearTimeout(debounceTimer);
                debounceTimer = window.setTimeout(applyRealtimeFilters, 1000);
            });
            qInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    applyRealtimeFilters();
                }
            });
        }

        [estadoSelect, tipoSelect, repartidorSelect, fechaDesde, fechaHasta].forEach(function (el) {
            if (!el) return;
            el.addEventListener('change', applyRealtimeFilters);
        });

        var btnAbrirReponerTodo = document.getElementById('btnAbrirReponerTodo');
        if (btnAbrirReponerTodo) {
            btnAbrirReponerTodo.addEventListener('click', function () {
                var values = getFilterValues();
                syncHiddenTodoInputs(values);

                var url = new URL('/devoluciones/resumen-reponer-todo/', window.location.origin);
                Object.keys(values).forEach(function (k) {
                    if (values[k]) url.searchParams.set(k, values[k]);
                });

                fetch(url.toString(), {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                })
                    .then(function (res) { return res.json(); })
                    .then(function (data) {
                        renderResumen('repTodoResumenBody', 'repTodoTotalItems', 'repTodoTotalAumenta', data.resumen || {});
                        $('#modalReponerTodo').modal('show');
                    })
                    .catch(function () {
                        window.alert('No se pudo cargar el resumen de reposicion masiva');
                    });
            });
        }

        var formReponerTodo = document.getElementById('formReponerTodo');
        if (formReponerTodo) {
            formReponerTodo.addEventListener('submit', function (e) {
                if (!window.confirm('Se repondra al stock todo lo pendiente segun los filtros actuales. Deseas continuar?')) {
                    e.preventDefault();
                }
            });
        }
    });
})();
