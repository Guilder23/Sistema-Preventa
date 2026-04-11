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
        document.querySelectorAll('#itemsPedidoEditarBody tr').forEach((tr) => {
            const subEl = tr.querySelector('.item-subtotal');
            total += parsePrecio(subEl?.value);
        });
        const totalEl = document.getElementById('pedidoEditarTotal');
        if (totalEl) totalEl.textContent = total.toFixed(2);
    }

    function wireFila(tr) {
        tr.addEventListener('change', function (e) {
            if (e.target.classList.contains('item-producto') || e.target.classList.contains('item-cantidad')) {
                calcularFila(tr);
                calcularTotal();
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
            tr.querySelector('.item-producto').value = String(productoId);
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
        $(document).on('click', '.btn-editar-pedido', function (e) {
            e.preventDefault();
            const id = $(this).data('pedido-id');
            if (!id) return;
            cargarPedido(id);
        });

        const btnAdd = document.getElementById('btnAgregarItemEditar');
        if (btnAdd) btnAdd.addEventListener('click', function () { agregarFila(); });

        $('#modalEditarPedido').on('hidden.bs.modal', resetModal);
    });
})();
