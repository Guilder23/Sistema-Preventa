document.addEventListener('DOMContentLoaded', function () {
    const input = document.getElementById('buscarProducto');
    if (input) {
        let t;
        input.addEventListener('input', function () {
            clearTimeout(t);
            t = setTimeout(() => {
                const q = (input.value || '').trim();
                const url = new URL(window.location.href);
                if (q) url.searchParams.set('q', q);
                else url.searchParams.delete('q');
                window.location.href = url.toString();
            }, 250);
        });
    }
});
