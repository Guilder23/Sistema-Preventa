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
        window.location.href = window.location.pathname + next;
    }

    function debounceApply() {
        if (debounceTimer) {
            window.clearTimeout(debounceTimer);
        }
        debounceTimer = window.setTimeout(applyFilters, 350);
        updatePdfLink();
    }

    inputs.forEach(function (el) {
        if (el.tagName === "SELECT" || el.type === "date") {
            el.addEventListener("change", debounceApply);
        } else {
            el.addEventListener("input", debounceApply);
        }
    });

    // Sin botón Filtrar: intercepta submit por si enter en el input
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        applyFilters();
    });

    updatePdfLink();
})();
