// ================================================================
// MODAL EDITAR USUARIO - VERSIÓN SIMPLIFICADA
// ================================================================

(function() {
    'use strict';
    
    // Esperar a que jQuery esté listo
    $(document).ready(function() {
        
        // Delegación de eventos para botones de editar (dinámicos)
        $(document).on('click', '.btn-editar-usuario', function(e) {
            e.preventDefault();
            const userId = $(this).data('usuario-id');
            cargarDatosUsuario(userId);
        });
        
        // Inicializar eventos cuando se muestra el modal
        $('#modalEditarUsuario').on('shown.bs.modal', function() {
            
            // Event listener para cambio de rol
            $('#editRol').off('change').on('change', function() {
                const rolSeleccionado = $(this).val();
                mostrarOcultarSelectoresEditar(rolSeleccionado);
            });
            
            // Event listener para submit del formulario
            $('#formEditarUsuario').off('submit').on('submit', function(e) {
                if (!validarFormularioEditar()) {
                    e.preventDefault();
                    return false;
                }
                
                // Configurar action del formulario dinámicamente
                const userId = $('#editarUsuarioId').val();
                const form = $(this);
                form.attr('action', `/usuarios/${userId}/editar/`);
            });
        });
        
        // Limpiar cuando se cierra el modal
        $('#modalEditarUsuario').on('hidden.bs.modal', function() {
            $('#formEditarUsuario')[0].reset();
            $('#editGrupoSupervisor').hide();
        });
    });
    
    function cargarDatosUsuario(userId) {
        
        $.ajax({
            url: `/usuarios/${userId}/obtener/`,
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                
                // Llenar el formulario
                $('#editarUsuarioId').val(data.id);
                $('#editUsername').val(data.username);
                $('#editEmail').val(data.email);
                $('#editFirstName').val(data.first_name || '');
                $('#editLastName').val(data.last_name || '');
                $('#editRol').val(data.rol);
                $('#editSupervisorId').val(data.supervisor_id || '');
                $('#editIsActive').prop('checked', data.is_active);
                
                // Mostrar los selectores según el rol
                mostrarOcultarSelectoresEditar(data.rol);
                
                // Seleccionar almacén o tienda si aplica
                if (data.almacen_id) {
                    $('#editAlmacen').val(data.almacen_id);
                }
                if (data.tienda_id) {
                    $('#editTienda').val(data.tienda_id);
                }
                
                // Abrir el modal
                $('#modalEditarUsuario').modal('show');
            },
            error: function(xhr, status, error) {
                alert('Error al cargar los datos del usuario');
            }
        });
    }
    
    function mostrarOcultarSelectoresEditar(rol) {
        console.log('→ mostrarOcultarSelectoresEditar(' + rol + ')');

        const $grupoSupervisor = $('#editGrupoSupervisor');
        const $selectSupervisor = $('#editSupervisorId');

        $grupoSupervisor.hide();
        $selectSupervisor.removeAttr('required');

        if (rol === 'preventista') {
            $grupoSupervisor.show();
        } else {
            $selectSupervisor.val('');
        }
    }
    
    function validarFormularioEditar() {
        console.log('→ Validando formulario editar...');
        
        const username = $('#editUsername').val().trim();
        const email = $('#editEmail').val().trim();
        const rol = $('#editRol').val();
        
        // Validar campos requeridos
        if (!username || !email || !rol) {
            alert('Por favor complete todos los campos requeridos');
            console.log('✗ Campos incompletos');
            return false;
        }
        
        // El supervisor es opcional para Preventista.
        
        console.log('✓ Formulario editar válido - enviando...');
        return true;
    }
    
})();
