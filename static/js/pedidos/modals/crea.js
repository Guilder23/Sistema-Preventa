(function () {
    'use strict';

    function setInlineError(msg) {
        const el = document.getElementById('pedidoCrearError');
        if (!el) return;
        if (!msg) {
            el.textContent = '';
            el.classList.add('d-none');
        } else {
            el.textContent = msg;
            el.classList.remove('d-none');
        }
    }

    function ensureAutocompleteStyles() {
        // no-op: estilos en css
    }

    function normalizeText(s) {
        return (s || '').toString().trim().toLowerCase();
    }

    function createDropdown(inputEl) {
        const wrap = document.createElement('div');
        wrap.className = 'ac-wrap';
        inputEl.parentNode.insertBefore(wrap, inputEl);
        wrap.appendChild(inputEl);

        const dd = document.createElement('div');
        dd.className = 'ac-dropdown d-none';
        wrap.appendChild(dd);

        return dd;
    }

    function attachAutocomplete({ inputEl, hiddenIdEl, items, onPick }) {
        if (!inputEl || !hiddenIdEl) return;

        const dropdownEl = createDropdown(inputEl);
        let activeIndex = -1;
        let filtered = [];

        function hide() {
            dropdownEl.classList.add('d-none');
            dropdownEl.innerHTML = '';
            activeIndex = -1;
        }

        function show() {
            dropdownEl.classList.remove('d-none');
        }

        function render() {
            dropdownEl.innerHTML = '';
            filtered.slice(0, 12).forEach((it, idx) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'ac-item';
                if (idx === activeIndex) btn.classList.add('active');
                btn.textContent = it.label;
                btn.addEventListener('mousedown', function (e) {
                    e.preventDefault();
                    pick(it);
                });
                dropdownEl.appendChild(btn);
            });

            if (filtered.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'ac-empty';
                empty.textContent = 'Sin resultados';
                dropdownEl.appendChild(empty);
            }
        }

        function applyFilter() {
            const term = normalizeText(inputEl.value);
            if (!term) {
                filtered = (items || []).slice(0, 30);
            } else {
                filtered = (items || []).filter((it) => normalizeText(it.label).includes(term));
            }
            activeIndex = filtered.length ? 0 : -1;
            render();
            show();
        }

        function pick(it) {
            inputEl.value = it.label;
            hiddenIdEl.value = String(it.id);
            inputEl.classList.remove('is-invalid');
            hide();
            if (typeof onPick === 'function') onPick(it);
        }

        function validateExact() {
            const label = (inputEl.value || '').trim();
            const match = (items || []).find((it) => String(it.label) === String(label));
            if (!match) {
                hiddenIdEl.value = '';
                inputEl.classList.add('is-invalid');
                return false;
            }
            hiddenIdEl.value = String(match.id);
            inputEl.classList.remove('is-invalid');
            return true;
        }

        inputEl.addEventListener('focus', function () {
            applyFilter();
        });

        inputEl.addEventListener('input', function () {
            hiddenIdEl.value = '';
            inputEl.classList.remove('is-invalid');
            applyFilter();
        });

        inputEl.addEventListener('keydown', function (e) {
            if (dropdownEl.classList.contains('d-none')) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!filtered.length) return;
                activeIndex = Math.min(activeIndex + 1, Math.min(filtered.length, 12) - 1);
                render();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!filtered.length) return;
                activeIndex = Math.max(activeIndex - 1, 0);
                render();
            } else if (e.key === 'Enter') {
                if (activeIndex >= 0 && filtered[activeIndex]) {
                    e.preventDefault();
                    pick(filtered[activeIndex]);
                }
            } else if (e.key === 'Escape') {
                hide();
            }
        });

        inputEl.addEventListener('blur', function () {
            // Delay para permitir click en opciones (mousedown ya pickea)
            window.setTimeout(function () {
                validateExact();
                hide();
            }, 120);
        });

        return { validateExact, pick };
    }

    function safeJsonParseScriptTag(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try {
            return JSON.parse(el.textContent || 'null');
        } catch {
            return null;
        }
    }

    function fillDatalist(datalistEl, items) {
        if (!datalistEl) return;
        datalistEl.innerHTML = '';
        (items || []).forEach((it) => {
            const opt = document.createElement('option');
            opt.value = it.label;
            datalistEl.appendChild(opt);
        });
    }

    function buildMaps(items) {
        const byLabel = new Map();
        const byId = new Map();
        (items || []).forEach((it) => {
            if (it && it.label != null) byLabel.set(String(it.label), it);
            if (it && it.id != null) byId.set(String(it.id), it);
        });
        return { byLabel, byId };
    }

    function parsePrecio(v) {
        const n = parseFloat((v || '0').toString().replace(',', '.'));
        return Number.isFinite(n) ? n : 0;
    }

    function calcularFila(tr) {
        const prodIdEl = tr.querySelector('.item-producto-id');
        const prodBuscarEl = tr.querySelector('.item-producto-buscar');
        const stockEl = tr.querySelector('.item-stock');
        const precioEl = tr.querySelector('.item-precio');
        const cantEl = tr.querySelector('.item-cantidad');
        const subEl = tr.querySelector('.item-subtotal');

        const productoId = (prodIdEl?.value || '').trim();
        const prod = productoId ? (window.__pedidosProductosById?.get(productoId) || null) : null;
        const precio = parsePrecio(prod?.precio);
        const stock = Number.isFinite(parseInt(prod?.stock, 10)) ? parseInt(prod.stock, 10) : 0;
        const cant = parseInt(cantEl.value || '0', 10) || 0;
        const subtotal = precio * cant;

        if (stockEl) stockEl.value = String(stock);
        if (cantEl) {
            cantEl.max = stock > 0 ? String(stock) : '';
            if (stock > 0 && cant > stock) {
                cantEl.classList.add('is-invalid');
            } else {
                cantEl.classList.remove('is-invalid');
            }
        }

        if (prodBuscarEl && productoId && stock === 0) {
            // producto seleccionado sin stock
            prodBuscarEl.classList.add('is-invalid');
        } else {
            prodBuscarEl?.classList.remove('is-invalid');
        }

        precioEl.value = precio.toFixed(2);
        subEl.value = subtotal.toFixed(2);
    }

    function calcularTotal() {
        let total = 0;
        document.querySelectorAll('#itemsPedidoBody tr').forEach((tr) => {
            const subEl = tr.querySelector('.item-subtotal');
            total += parsePrecio(subEl?.value);
        });
        const totalEl = document.getElementById('pedidoTotal');
        if (totalEl) totalEl.textContent = total.toFixed(2);
    }

    function agregarFila() {
        const tpl = document.getElementById('tplItemPedido');
        const body = document.getElementById('itemsPedidoBody');
        if (!tpl || !body) return;

        const fragment = tpl.content.cloneNode(true);
        const tr = fragment.querySelector('tr');

        body.appendChild(fragment);

        // recalcular la última fila agregada
        const last = body.querySelector('tr:last-child');
        if (!last) return;

        const prodBuscarEl = last.querySelector('.item-producto-buscar');
        const prodIdEl = last.querySelector('.item-producto-id');

        attachAutocomplete({
            inputEl: prodBuscarEl,
            hiddenIdEl: prodIdEl,
            items: window.__pedidosProductosData || [],
            onPick: function () {
                setInlineError('');
                calcularFila(last);
                calcularTotal();
            },
        });

        last.querySelector('.item-cantidad')?.addEventListener('input', function () {
            setInlineError('');
            calcularFila(last);
            calcularTotal();
        });
        last.querySelector('.btn-quitar-item')?.addEventListener('click', function () {
            last.remove();
            calcularTotal();
        });

        calcularFila(last);
        calcularTotal();
    }

    document.addEventListener('DOMContentLoaded', function () {
        ensureAutocompleteStyles();

        const clientesData = safeJsonParseScriptTag('clientes-data-pedidos') || [];
        const productosData = safeJsonParseScriptTag('productos-data-pedidos') || [];

        const clientesMaps = buildMaps(clientesData);
        const productosMaps = buildMaps(productosData);
        window.__pedidosClientesByLabel = clientesMaps.byLabel;
        window.__pedidosProductosByLabel = productosMaps.byLabel;
        window.__pedidosProductosById = productosMaps.byId;
        window.__pedidosProductosData = productosData;

        fillDatalist(document.getElementById('dlClientesPedidos'), clientesData);
        fillDatalist(document.getElementById('dlProductosPedidos'), productosData);

        const clienteBuscarEl = document.getElementById('pedidoClienteBuscar');
        const clienteIdEl = document.getElementById('pedidoClienteId');
        const acCliente = attachAutocomplete({
            inputEl: clienteBuscarEl,
            hiddenIdEl: clienteIdEl,
            items: clientesData,
        });

        clienteBuscarEl?.addEventListener('input', function () {
            setInlineError('');
        });

        const btnAdd = document.getElementById('btnAgregarItem');
        if (btnAdd) btnAdd.addEventListener('click', agregarFila);

        const form = document.getElementById('formCrearPedido');
        if (form) {
            form.addEventListener('submit', function (e) {
                const okCliente = acCliente ? acCliente.validateExact() : true;
                let okProductos = true;
                document.querySelectorAll('#itemsPedidoBody tr').forEach((tr) => {
                    const buscarEl = tr.querySelector('.item-producto-buscar');
                    const idEl = tr.querySelector('.item-producto-id');
                    const cantEl = tr.querySelector('.item-cantidad');
                    if (!buscarEl || !idEl) return;
                    const label = (buscarEl.value || '').trim();
                    const match = (window.__pedidosProductosData || []).find((it) => String(it.label) === String(label));
                    if (!match) {
                        idEl.value = '';
                        buscarEl.classList.add('is-invalid');
                        okProductos = false;
                    } else {
                        idEl.value = String(match.id);
                        buscarEl.classList.remove('is-invalid');

                        const stock = parseInt(match.stock || '0', 10) || 0;
                        const cant = parseInt(cantEl?.value || '0', 10) || 0;
                        if (cantEl && stock > 0 && cant > stock) {
                            cantEl.classList.add('is-invalid');
                            okProductos = false;
                        }
                        if (stock === 0) {
                            buscarEl.classList.add('is-invalid');
                            okProductos = false;
                        }
                    }
                });

                if (!okCliente || !okProductos) {
                    e.preventDefault();
                    setInlineError('Verifica: cliente válido, productos válidos y stock suficiente.');
                }
            });
        }

        $('#modalCrearPedido').on('shown.bs.modal', function () {
            const body = document.getElementById('itemsPedidoBody');
            if (body && body.children.length === 0) {
                agregarFila();
            }
        });

        $('#modalCrearPedido').on('hidden.bs.modal', function () {
            const form = document.getElementById('formCrearPedido');
            const body = document.getElementById('itemsPedidoBody');
            if (form) form.reset();
            if (body) body.innerHTML = '';
            const totalEl = document.getElementById('pedidoTotal');
            if (totalEl) totalEl.textContent = '0.00';

            const clienteIdEl = document.getElementById('pedidoClienteId');
            if (clienteIdEl) clienteIdEl.value = '';

            const clienteBuscarEl = document.getElementById('pedidoClienteBuscar');
            if (clienteBuscarEl) clienteBuscarEl.classList.remove('is-invalid');

            setInlineError('');
        });
    });
})();
