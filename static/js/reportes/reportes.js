(function () {
    var form = document.getElementById("filtro-reportes");
    if (!form) {
        return;
    }

    var pdfBtns = document.querySelectorAll(".btn-pdf-reportes");
    var inputs = form.querySelectorAll("input[name], select[name]");

    function buildParams() {
        var params = new URLSearchParams();
        inputs.forEach(function (el) {
            if (el.disabled) return;
            var value = (el.value || "").trim();
            if (value) {
                params.set(el.name, value);
            }
        });
        return params;
    }

    function updatePdfLink() {
        if (!pdfBtns.length) {
            return;
        }
        var params = buildParams();
        pdfBtns.forEach(function (btn) {
            var baseUrl = form.getAttribute("data-pdf-url") || btn.getAttribute("href") || "";
            if (baseUrl.indexOf("?") !== -1) {
                baseUrl = baseUrl.split("?")[0];
            }
            var href = baseUrl;
            if (params.toString()) {
                href += "?" + params.toString();
            }
            btn.setAttribute("href", href);
        });
    }

    var debounceTimer = null;
    function applyFilters() {
        var params = buildParams();
        var next = params.toString() ? ("?" + params.toString()) : "";
        var current = window.location.search || "";
        if (current === next) {
            updatePdfLink();
            return;
        }

        // Guardar información de foco usando el ID del elemento
        var activeInput = document.activeElement;
        if (activeInput && activeInput.name === 'q') {
            sessionStorage.setItem('reportSearchFocusId', activeInput.id);
        }

        window.location.href = window.location.pathname + next;
    }

    // Restaurar foco con un pequeño retraso para asegurar que los inputs estén habilitados por tabs.js
    function restoreFocus() {
        var focusId = sessionStorage.getItem('reportSearchFocusId');
        if (focusId) {
            setTimeout(function() {
                var el = document.getElementById(focusId);
                if (el) {
                    el.focus();
                    var val = el.value;
                    el.value = '';
                    el.value = val;
                }
                sessionStorage.removeItem('reportSearchFocusId');
            }, 150);
        }
    }

    // Ejecutar restauración al cargar
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', restoreFocus);
    } else {
        restoreFocus();
    }

    function debounceApply() {
        if (debounceTimer) {
            window.clearTimeout(debounceTimer);
        }
        debounceTimer = window.setTimeout(applyFilters, 1000);
        updatePdfLink();
    }

    inputs.forEach(function (el) {
        if (el.tagName === "SELECT" || el.type === "date") {
            el.addEventListener("change", function() {
                clearTimeout(debounceTimer);
                applyFilters();
            });
        } else {
            el.addEventListener("input", debounceApply);
            el.addEventListener("keypress", function (e) {
                if (e.key === 'Enter') {
                    clearTimeout(debounceTimer);
                    applyFilters();
                }
            });
        }
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        applyFilters();
    });

    updatePdfLink();
})();
