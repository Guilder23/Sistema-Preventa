/**
 * BASE.JS - Scripts del layout principal
 */

(function() {
    'use strict';

    /**
     * Auto-cerrar mensajes después de 4 segundos
     */
    function autoCerrarMensajes() {
        const alerts = document.querySelectorAll('.messages-container .alert');

        console.log('base.js: Mensajes encontrados:', alerts.length);

        if (alerts.length === 0) {
            console.log('base.js: No hay mensajes para mostrar');
            return;
        }

        alerts.forEach(function(alert, index) {
            console.log('base.js: Procesando alerta', index + 1);

            // Auto-cerrar después de 4 segundos
            setTimeout(function() {
                console.log('base.js: Cerrando alerta', index + 1);
                alert.classList.add('fade-out');

                // Remover del DOM después de la animación
                setTimeout(function() {
                    if (alert.parentElement) {
                        alert.remove();
                        console.log('base.js: Alerta removida', index + 1);
                    }
                }, 300);
            }, 4000);
        });
    }

    /**
     * Evitar warnings aria-hidden en modales moviendo el foco
     */
    function gestionarFocusModals() {
        let ultimoFoco = null;

        document.addEventListener('show.bs.modal', function() {
            ultimoFoco = document.activeElement;
        });

        document.addEventListener('hide.bs.modal', function(event) {
            const modal = event.target;
            if (modal && modal.contains(document.activeElement)) {
                document.activeElement.blur();
            }
        });

        document.addEventListener('hidden.bs.modal', function() {
            if (ultimoFoco && typeof ultimoFoco.focus === 'function') {
                ultimoFoco.focus();
            }
            ultimoFoco = null;
        });
    }

    gestionarFocusModals();

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        console.log('base.js: Esperando DOMContentLoaded');
        document.addEventListener('DOMContentLoaded', autoCerrarMensajes);
    } else {
        console.log('base.js: DOM ya está listo, ejecutando inmediatamente');
        autoCerrarMensajes();
    }

})();
