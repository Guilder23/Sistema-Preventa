(function () {
    'use strict';

    function previewFile(inputEl, imgEl) {
        if (!inputEl || !imgEl) return;
        const file = inputEl.files && inputEl.files[0];
        if (!file) {
            imgEl.src = '';
            imgEl.classList.add('d-none');
            return;
        }
        const url = URL.createObjectURL(file);
        imgEl.src = url;
        imgEl.classList.remove('d-none');
        imgEl.onload = function () {
            try { URL.revokeObjectURL(url); } catch (e) { /* ignore */ }
        };
    }

    $(document).ready(function () {
        const input = document.getElementById('createFoto');
        const img = document.getElementById('createFotoPreview');
        if (input && img) {
            input.addEventListener('change', function () {
                previewFile(input, img);
            });
        }

        $('#modalCrearProducto').on('hidden.bs.modal', function () {
            if (input) input.value = '';
            if (img) {
                img.src = '';
                img.classList.add('d-none');
            }
        });
    });
})();
