/* ============================================================================
   FUNCIONALIDAD PARA NAVBAR - DROPDOWNS MODERNOS
   ============================================================================ */

function inicializarNavbar() {
    const comunicadosBtn = document.getElementById("comunicadosBtn");
    const comunicadosDropdown = document.getElementById("comunicadosDropdown");
    const notificacionesBtn = document.getElementById("notificacionesBtn");
    const notificacionesDropdown = document.getElementById("notificacionesDropdown");
    const usuarioBtn = document.getElementById("usuarioBtn");
    const usuarioDropdown = document.getElementById("usuarioDropdown");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    // Toggle dropdown de comunicados
    if (comunicadosBtn && comunicadosDropdown) {
        comunicadosBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (usuarioDropdown) usuarioDropdown.classList.remove("show");
            if (notificacionesDropdown) notificacionesDropdown.classList.remove("show", "mostrar");
            comunicadosDropdown.classList.toggle("show");
            comunicadosDropdown.classList.toggle("mostrar");
        });
    }

    // Toggle dropdown de notificaciones
    if (notificacionesBtn && notificacionesDropdown) {
        notificacionesBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (usuarioDropdown) usuarioDropdown.classList.remove("show");
            if (comunicadosDropdown) comunicadosDropdown.classList.remove("show", "mostrar");
            notificacionesDropdown.classList.toggle("show");
            notificacionesDropdown.classList.toggle("mostrar");
        });
    }

    // Toggle dropdown de usuario
    if (usuarioBtn && usuarioDropdown) {
        usuarioBtn.addEventListener("click", function(e) {
            e.preventDefault();
            e.stopPropagation();
            if (comunicadosDropdown) comunicadosDropdown.classList.remove("show", "mostrar");
            if (notificacionesDropdown) notificacionesDropdown.classList.remove("show", "mostrar");
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
        if (comunicadosDropdown && comunicadosBtn && !comunicadosBtn.contains(e.target) && !comunicadosDropdown.contains(e.target)) {
            comunicadosDropdown.classList.remove("show", "mostrar");
        }
        if (notificacionesDropdown && notificacionesBtn && !notificacionesBtn.contains(e.target) && !notificacionesDropdown.contains(e.target)) {
            notificacionesDropdown.classList.remove("show", "mostrar");
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
