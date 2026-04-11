/* ============================================================================
   FUNCIONALIDAD PARA NAVBAR - DROPDOWNS MODERNOS
   ============================================================================ */

function inicializarNavbar() {
    const usuarioBtn = document.getElementById("usuarioBtn");
    const usuarioDropdown = document.getElementById("usuarioDropdown");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    // Toggle dropdown de usuario
    if (usuarioBtn && usuarioDropdown) {
        usuarioBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            usuarioDropdown.classList.toggle("show");
        });
    }

    // Sidebar Toggle
    if (sidebarToggle && sidebar && sidebarOverlay) {
        sidebarToggle.addEventListener("click", function() {
            sidebar.classList.toggle("active");
            sidebarOverlay.classList.toggle("active");
        });

        sidebarOverlay.addEventListener("click", function() {
            sidebar.classList.remove("active");
            sidebarOverlay.classList.remove("active");
        });
    }

    // Cerrar dropdowns al hacer clic fuera
    document.addEventListener("click", function(e) {
        if (usuarioDropdown && usuarioBtn && !usuarioBtn.contains(e.target) && !usuarioDropdown.contains(e.target)) {
            usuarioDropdown.classList.remove("show");
        }
    });

    // Escuchar cambios en tamaño de ventana
    window.addEventListener("resize", function() {
        if (window.innerWidth > 992) {
            if (sidebar && sidebarOverlay) {
                sidebar.classList.remove("active");
                sidebarOverlay.classList.remove("active");
            }
        }
    });
}

// Inicializar navbar cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", inicializarNavbar);
