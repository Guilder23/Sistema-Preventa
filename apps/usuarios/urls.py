from django.urls import path

from . import views


urlpatterns = [
    path("inicio/", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("recuperar-password/", views.recuperar_password, name="recuperar_password"),
    path(
        "recuperar-password/<uidb64>/<token>/",
        views.recuperar_password_confirmar,
        name="recuperar_password_confirmar",
    ),
    path(
        "recuperar-password/completado/",
        views.recuperar_password_completado,
        name="recuperar_password_completado",
    ),

    path("perfil/", views.mi_perfil, name="mi_perfil"),

    # Gestión de usuarios
    path("usuarios/", views.listar_usuarios, name="listar_usuarios"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/<int:id>/obtener/", views.obtener_usuario, name="obtener_usuario"),
    path("usuarios/<int:id>/editar/", views.editar_usuario, name="editar_usuario"),
    path("usuarios/<int:id>/eliminar/", views.bloquear_usuario, name="eliminar_usuario"),
    path("usuarios/<int:id>/bloquear/", views.bloquear_usuario, name="bloquear_usuario"),
]
