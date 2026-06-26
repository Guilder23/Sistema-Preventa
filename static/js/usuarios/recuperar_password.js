document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');
    forms.forEach(function (form) {
        form.addEventListener('submit', function () {
            const button = form.querySelector('button[type="submit"]');
            if (button) {
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
            }
        });
    });
});
