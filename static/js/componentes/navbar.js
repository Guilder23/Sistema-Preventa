/* ============================================================================
   FUNCIONALIDAD PARA NAVBAR - DROPDOWNS MODERNOS
   ============================================================================ */

function inicializarNavbar() {
    const usuarioBtn = document.getElementById("usuarioBtn");
    const usuarioDropdown = document.getElementById("usuarioDropdown");

    // Toggle dropdown de usuario
    if (usuarioBtn && usuarioDropdown) {
        usuarioBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            usuarioDropdown.classList.toggle("show");
        });
    }

    // Cerrar dropdowns al hacer clic fuera
    document.addEventListener("click", function(e) {
        if (usuarioDropdown && usuarioBtn && !usuarioBtn.contains(e.target) && !usuarioDropdown.contains(e.target)) {
            usuarioDropdown.classList.remove("show");
        }
    });
}

// Inicializar navbar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", inicializarNavbar);
