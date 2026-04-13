/* ========================================
   CENTRO DE AYUDA - JAVASCRIPT
   ======================================== */

document.addEventListener('DOMContentLoaded', function() {
    /** GESTIÓN DE TABS DE ROLES */
    const tabsRoles = document.querySelectorAll('.tab-rol');
    const rolesContenido = document.querySelectorAll('.rol-contenido');

    tabsRoles.forEach(tab => {
        tab.addEventListener('click', function() {
            const rolSeleccionado = this.getAttribute('data-rol');

            // Remover clase active de todos los tabs
            tabsRoles.forEach(t => t.classList.remove('active'));
            rolesContenido.forEach(c => c.classList.remove('active'));

            // Agregar clase active al tab clickeado y su contenido
            this.classList.add('active');
            document.querySelector(`.rol-contenido[data-rol="${rolSeleccionado}"]`).classList.add('active');

            // Limpiar búsqueda al cambiar de tab
            document.getElementById('busquedaAyuda').value = '';
            document.getElementById('resultadosBusqueda').innerHTML = '';
            document.getElementById('resultadosBusqueda').classList.remove('active');
        });
    });

    /** BÚSQUEDA EN TIEMPO REAL */
    const busquedaInput = document.getElementById('busquedaAyuda');
    const resultadosContainer = document.getElementById('resultadosBusqueda');

    // Todos los elementos buscables
    const seccionesSearchable = document.querySelectorAll('.seccion-searchable');
    const conceptosSearchable = document.querySelectorAll('.concepto-searchable');
    const todosSearchable = [...seccionesSearchable, ...conceptosSearchable];

    busquedaInput.addEventListener('input', function() {
        const termino = this.value.toLowerCase().trim();

        if (termino.length < 2) {
            resultadosContainer.innerHTML = '';
            resultadosContainer.classList.remove('active');
            return;
        }

        // Buscar en todos los elementos
        const resultados = [];

        todosSearchable.forEach(elemento => {
            let titulo = '';
            let subtitulo = '';
            let contenido = '';

            // Obtener el título y contenido según el tipo de elemento
            if (elemento.classList.contains('seccion-searchable')) {
                titulo = elemento.querySelector('.seccion-header h3')?.textContent || '';
                subtitulo = elemento.getAttribute('data-seccion') || '';
                contenido = elemento.textContent;
            } else if (elemento.classList.contains('concepto-searchable')) {
                titulo = elemento.querySelector('h3')?.textContent || '';
                subtitulo = elemento.getAttribute('data-concepto') || '';
                contenido = elemento.textContent;
            }

            // Verificar si el término coincide
            if (titulo.toLowerCase().includes(termino) ||
                contenido.toLowerCase().includes(termino)) {
                resultados.push({
                    titulo: titulo,
                    subtitulo: subtitulo,
                    elemento: elemento
                });
            }
        });

        // Mostrar resultados
        mostrarResultados(resultados, termino);
    });

    function mostrarResultados(resultados, termino) {
        resultadosContainer.innerHTML = '';

        if (resultados.length === 0) {
            resultadosContainer.innerHTML = `
                <div class="no-resultados">
                    <i class="fas fa-search" style="margin-right: 0.5rem;"></i>
                    No se encontraron resultados para "${termino}"
                </div>
            `;
        } else {
            resultados.forEach(resultado => {
                const item = document.createElement('div');
                item.className = 'resultado-item';
                
                // Resaltar el término en el título
                const tituloResaltado = resultado.titulo.replace(
                    new RegExp(`(${termino})`, 'gi'),
                    '<span class="highlight">$1</span>'
                );

                item.innerHTML = `
                    <strong>${tituloResaltado}</strong>
                    <small>${resultado.subtitulo}</small>
                `;

                item.addEventListener('click', function() {
                    // Desplazarse al elemento
                    resultado.elemento.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    
                    // Resaltar temporalmente
                    resultado.elemento.style.backgroundColor = 'rgba(245, 158, 11, 0.1)';
                    setTimeout(() => {
                        resultado.elemento.style.backgroundColor = '';
                    }, 2000);

                    // Limpiar búsqueda
                    busquedaInput.value = '';
                    resultadosContainer.classList.remove('active');
                });

                resultadosContainer.appendChild(item);
            });
        }

        resultadosContainer.classList.add('active');
    }

    // Cerrar resultados al hacer click fuera
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.busqueda-contenedor')) {
            resultadosContainer.classList.remove('active');
        }
    });

    /** EXPANDIR/CONTRAER SECCIONES (OPCIONAL) */
    const seccionCards = document.querySelectorAll('.seccion-card');
    seccionCards.forEach(card => {
        card.addEventListener('click', function(e) {
            // Solo si no es un enlace
            if (!e.target.closest('a')) {
                this.style.maxHeight = this.style.maxHeight ? '' : this.scrollHeight + 'px';
            }
        });
    });

    /** COPIAR INFORMACIÓN DE CONTACTO */
    document.querySelectorAll('.soporte-enlace').forEach(enlace => {
        enlace.addEventListener('mouseenter', function() {
            // Agregar efecto visual
            this.style.transform = 'translateX(3px)';
        });
    });

    /** SMOOTH SCROLL PARA ENLACES INTERNOS */
    document.querySelectorAll('a[href^="#"]').forEach(enlace => {
        enlace.addEventListener('click', function(e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    /** FILTRAR POR ROL ACTUAL */
    const rolActual = busquedaInput.getAttribute('data-role');
    if (rolActual && rolActual !== '') {
        // El rol está guardado en data-role del input
        // Se puede usar para pre-seleccionar el tab correcto
    }

    /** MEJORAR ACCESIBILIDAD */
    tabsRoles.forEach(tab => {
        tab.setAttribute('type', 'button');
        tab.setAttribute('role', 'tab');
    });

    rolesContenido.forEach(contenido => {
        contenido.setAttribute('role', 'tabpanel');
    });

    /** BUSCA SIMPLE - FUNCIÓN AUXILIAR */
    window.buscarEnAyuda = function(termino) {
        busquedaInput.value = termino;
        busquedaInput.dispatchEvent(new Event('input'));
        busquedaInput.focus();
    };

    console.log('Centro de Ayuda inicializado correctamente');
});
