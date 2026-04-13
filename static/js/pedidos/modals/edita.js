(function () {
    'use strict';

    function setInlineError(msg) {
        const el = document.getElementById('pedidoEditarError');
        if (!el) return;
        if (!msg) {
            el.textContent = '';
            el.classList.add('d-none');
        } else {
            el.textContent = msg;
            el.classList.remove('d-none');
        }
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
        dd.className = 'ac-dropdown ac-dropdown-floating d-none';
        document.body.appendChild(dd);

        function place() {
            const rect = inputEl.getBoundingClientRect();
            const width = rect.width;
            const maxLeft = Math.max(8, window.innerWidth - width - 8);
            const left = Math.min(Math.max(rect.left, 8), maxLeft);

            dd.style.left = `${left}px`;
            dd.style.top = `${rect.bottom + 4}px`;
            dd.style.width = `${width}px`;
        }

        return { el: dd, place };
    }

    function attachAutocomplete({ inputEl, hiddenIdEl, items, onPick }) {
        if (!inputEl || !hiddenIdEl) return null;

        const dropdown = createDropdown(inputEl);
        const dropdownEl = dropdown.el;
        let activeIndex = -1;
        let filtered = [];

        function hide() {
            dropdownEl.classList.add('d-none');
            dropdownEl.innerHTML = '';
            activeIndex = -1;
        }

        function show() {
            dropdown.place();
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

            dropdown.place();
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

        inputEl.addEventListener('focus', applyFilter);
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
            window.setTimeout(function () {
                validateExact();
                hide();
            }, 120);
        });

        return { validateExact };
    }

    function parsePrecio(v) {
        const n = parseFloat((v || '0').toString().replace(',', '.'));
        return Number.isFinite(n) ? n : 0;
    }

    function getNombreProductoPorId(id) {
        const prod = id ? (window.__pedidosProductosById?.get(String(id)) || null) : null;
        if (!prod || !prod.label) return 'Producto';
        return String(prod.label);
    }

    function getProductoById(id) {
        return id ? (window.__pedidosProductosById?.get(String(id)) || null) : null;
    }

    function calcularFila(tr) {
        const prodIdEl = tr.querySelector('.item-producto-id');
        const stockEl = tr.querySelector('.item-stock');
        const precioEl = tr.querySelector('.item-precio');
        const cantEl = tr.querySelector('.item-cantidad');
        const subEl = tr.querySelector('.item-subtotal');

        const productoId = (prodIdEl?.value || '').trim();
        const prod = getProductoById(productoId);
        const precio = parsePrecio(prod?.precio);
        const stock = Number.isFinite(parseInt(prod?.stock, 10)) ? parseInt(prod.stock, 10) : 0;
        const cant = parseInt(cantEl.value || '0', 10) || 0;
        const subtotal = precio * cant;

        if (stockEl) stockEl.value = String(stock);
        if (cantEl) {
            cantEl.max = stock > 0 ? String(stock) : '';
            if (cant > stock) {
                cantEl.classList.add('is-invalid');
            } else {
                cantEl.classList.remove('is-invalid');
            }
        }

        const buscarEl = tr.querySelector('.item-producto-buscar');
        if (buscarEl && productoId && (stock === 0 || precio <= 0)) {
            buscarEl.classList.add('is-invalid');
        } else {
            buscarEl?.classList.remove('is-invalid');
        }

        precioEl.value = precio.toFixed(2);
        subEl.value = subtotal.toFixed(2);
    }

    function calcularTotal() {
        let total = 0;
        document.querySelectorAll('#itemsPedidoEditarBody tr').forEach((tr) => {
            const subEl = tr.querySelector('.item-subtotal');
            total += parsePrecio(subEl?.value);
        });
        const totalEl = document.getElementById('pedidoEditarTotal');
        if (totalEl) totalEl.textContent = total.toFixed(2);
    }

    function wireFila(tr) {
        const prodBuscarEl = tr.querySelector('.item-producto-buscar');
        const prodIdEl = tr.querySelector('.item-producto-id');

        attachAutocomplete({
            inputEl: prodBuscarEl,
            hiddenIdEl: prodIdEl,
            items: window.__pedidosProductosData || [],
            onPick: function () {
                setInlineError('');
                calcularFila(tr);
                calcularTotal();
            },
        });

        tr.querySelector('.item-cantidad')?.addEventListener('input', function () {
            setInlineError('');
            calcularFila(tr);
            calcularTotal();
        });

        tr.querySelector('.btn-cant-menos')?.addEventListener('click', function () {
            const cantEl = tr.querySelector('.item-cantidad');
            const actual = parseInt(cantEl?.value || '1', 10) || 1;
            const siguiente = Math.max(actual - 1, 1);
            if (cantEl) {
                cantEl.value = String(siguiente);
                cantEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });

        tr.querySelector('.btn-cant-mas')?.addEventListener('click', function () {
            const cantEl = tr.querySelector('.item-cantidad');
            const actual = parseInt(cantEl?.value || '1', 10) || 1;
            if (cantEl) {
                cantEl.value = String(actual + 1);
                cantEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });

        tr.querySelector('.btn-quitar-item')?.addEventListener('click', function () {
            tr.remove();
            calcularTotal();
        });
    }

    function agregarFila({ productoId, cantidad } = {}) {
        const tpl = document.getElementById('tplItemPedidoEditar');
        const body = document.getElementById('itemsPedidoEditarBody');
        if (!tpl || !body) return null;

        const fragment = tpl.content.cloneNode(true);
        body.appendChild(fragment);

        const tr = body.querySelector('tr:last-child');
        if (!tr) return null;

        wireFila(tr);

        if (productoId) {
            const prod = getProductoById(String(productoId));
            const buscarEl = tr.querySelector('.item-producto-buscar');
            const idEl = tr.querySelector('.item-producto-id');
            if (idEl) idEl.value = String(productoId);
            if (buscarEl) buscarEl.value = prod?.label ? String(prod.label) : '';
        }
        if (cantidad) {
            tr.querySelector('.item-cantidad').value = String(cantidad);
        }

        calcularFila(tr);
        calcularTotal();

        return tr;
    }

    function resetModal() {
        const form = document.getElementById('formEditarPedido');
        const body = document.getElementById('itemsPedidoEditarBody');
        if (form) form.reset();
        if (body) body.innerHTML = '';
        const totalEl = document.getElementById('pedidoEditarTotal');
        if (totalEl) totalEl.textContent = '0.00';
        const clienteEl = document.getElementById('editarPedidoCliente');
        if (clienteEl) clienteEl.value = '';

        document.querySelectorAll('.ac-dropdown-floating').forEach((el) => {
            el.classList.add('d-none');
        });

        setInlineError('');
    }

    function cargarPedido(id) {
        $.ajax({
            url: `/pedidos/${id}/obtener/`,
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                $('#editarPedidoId').val(data.id);
                $('#editarPedidoCliente').val(data.cliente || '');
                $('#editarPedidoObs').val(data.observacion || '');

                const body = document.getElementById('itemsPedidoEditarBody');
                if (body) body.innerHTML = '';

                const detalles = data.detalles || [];
                if (!detalles.length) {
                    agregarFila();
                } else {
                    detalles.forEach((d) => {
                        agregarFila({ productoId: d.producto_id, cantidad: d.cantidad });
                    });
                }

                const form = document.getElementById('formEditarPedido');
                if (form) form.setAttribute('action', `/pedidos/${data.id}/editar/`);

                $('#modalEditarPedido').modal('show');
            },
            error: function () {
                alert('Error al cargar el pedido');
            }
        });
    }

    $(document).ready(function () {
        // dataset viene del modal crear (json_script) y se comparte en window
        // si por algún motivo no está, intentamos llenar el datalist desde el script tag.
        try {
            const el = document.getElementById('productos-data-pedidos');
            if (el && (!window.__pedidosProductosById || !window.__pedidosProductosByLabel)) {
                const data = JSON.parse(el.textContent || '[]');
                const byLabel = new Map();
                const byId = new Map();
                (data || []).forEach((it) => {
                    if (it && it.label != null) byLabel.set(String(it.label), it);
                    if (it && it.id != null) byId.set(String(it.id), it);
                });
                window.__pedidosProductosByLabel = byLabel;
                window.__pedidosProductosById = byId;
                window.__pedidosProductosData = data;

                const dl = document.getElementById('dlProductosPedidos');
                if (dl && dl.children.length === 0) {
                    dl.innerHTML = '';
                    (data || []).forEach((it) => {
                        const opt = document.createElement('option');
                        opt.value = it.label;
                        dl.appendChild(opt);
                    });
                }
            }
        } catch {
            // ignore
        }

        $(document).on('click', '.btn-editar-pedido', function (e) {
            e.preventDefault();
            const id = $(this).data('pedido-id');
            if (!id) return;
            cargarPedido(id);
        });

        const btnAdd = document.getElementById('btnAgregarItemEditar');
        if (btnAdd) btnAdd.addEventListener('click', function () { agregarFila(); });

        $('#modalEditarPedido').on('hidden.bs.modal', resetModal);

        const form = document.getElementById('formEditarPedido');
        if (form) {
            form.addEventListener('submit', function (e) {
                let ok = true;
                const errores = [];
                let fila = 0;
                document.querySelectorAll('#itemsPedidoEditarBody tr').forEach((tr) => {
                    fila += 1;
                    const buscarEl = tr.querySelector('.item-producto-buscar');
                    const idEl = tr.querySelector('.item-producto-id');
                    const cantEl = tr.querySelector('.item-cantidad');
                    if (!buscarEl || !idEl) return;
                    const label = (buscarEl.value || '').trim();
                    const match = (window.__pedidosProductosData || []).find((it) => String(it.label) === String(label));
                    if (!match) {
                        idEl.value = '';
                        buscarEl.classList.add('is-invalid');
                        ok = false;
                        errores.push(`Fila ${fila}: selecciona un producto válido.`);
                    } else {
                        idEl.value = String(match.id);
                        buscarEl.classList.remove('is-invalid');

                        const nombreProducto = getNombreProductoPorId(match.id);
                        const stock = parseInt(match.stock || '0', 10) || 0;
                        const precio = parseFloat(match.precio || '0') || 0;
                        const cant = parseInt(cantEl?.value || '0', 10) || 0;
                        if (cantEl && cant > stock) {
                            cantEl.classList.add('is-invalid');
                            ok = false;
                            errores.push(`Fila ${fila} (${nombreProducto}): cantidad ${cant} supera stock ${stock}.`);
                        } else if (cantEl) {
                            cantEl.classList.remove('is-invalid');
                        }

                        if (stock === 0) {
                            buscarEl.classList.add('is-invalid');
                            ok = false;
                            errores.push(`Fila ${fila} (${nombreProducto}): stock agotado.`);
                        }

                        if (precio <= 0) {
                            buscarEl.classList.add('is-invalid');
                            ok = false;
                            errores.push(`Fila ${fila} (${nombreProducto}): no tiene precio de venta válido.`);
                        }
                    }
                });

                if (!ok) {
                    e.preventDefault();
                    setInlineError(errores.join(' | '));
                }
            });
        }
    });
})();
