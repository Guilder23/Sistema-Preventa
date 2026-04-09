(function () {
    'use strict';

    function parsePrecio(v) {
        const n = parseFloat((v || '0').toString().replace(',', '.'));
        return Number.isFinite(n) ? n : 0;
    }

    function calcularFila(tr) {
        const sel = tr.querySelector('.item-producto');
        const precioEl = tr.querySelector('.item-precio');
        const cantEl = tr.querySelector('.item-cantidad');
        const subEl = tr.querySelector('.item-subtotal');

        const opt = sel?.selectedOptions?.[0];
        const precio = parsePrecio(opt?.dataset?.precio);
        const cant = parseInt(cantEl.value || '0', 10) || 0;
        const subtotal = precio * cant;

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

        last.addEventListener('change', function (e) {
            if (e.target.classList.contains('item-producto') || e.target.classList.contains('item-cantidad')) {
                calcularFila(last);
                calcularTotal();
            }
        });
        last.querySelector('.btn-quitar-item')?.addEventListener('click', function () {
            last.remove();
            calcularTotal();
        });

        calcularFila(last);
        calcularTotal();
    }

    document.addEventListener('DOMContentLoaded', function () {
        const btnAdd = document.getElementById('btnAgregarItem');
        if (btnAdd) btnAdd.addEventListener('click', agregarFila);

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
        });
    });
})();
