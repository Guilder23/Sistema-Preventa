from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from decimal import Decimal

from apps.pedidos.models import Pedido
from apps.usuarios.models import PerfilUsuario

from .models import Cliente, TransferenciaCliente


class MapaClientesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin_mapa", password="test-password")
        self.admin.perfil.rol = "administrador"
        self.admin.perfil.activo = True
        self.admin.perfil.save(update_fields=["rol", "activo"])

        for indice in range(51):
            Cliente.objects.create(
                nombres=f"Cercano {indice:02d}",
                latitud=Decimal("-17.7800") + Decimal(indice) / Decimal("10000"),
                longitud=Decimal("-63.1800"),
            )
        Cliente.objects.create(
            nombres="Cliente lejano",
            latitud=Decimal("-17.5000"),
            longitud=Decimal("-63.1800"),
        )
        self.client.force_login(self.admin)

    def test_mapa_devuelve_los_50_clientes_mas_cercanos_y_reporta_el_resto(self):
        response = self.client.get(
            reverse("clientes_mapa_puntos"),
            {"lat": "-17.78", "lng": "-63.18"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["puntos"]), 50)
        self.assertEqual(data["total"], 51)
        self.assertTrue(data["hay_mas"])
        self.assertEqual(data["puntos"][0]["nombre"], "Cercano 00")
        self.assertNotIn("Cliente lejano", [punto["nombre"] for punto in data["puntos"]])

    def test_mapa_permite_cargar_todos_los_clientes_expresamente(self):
        response = self.client.get(reverse("clientes_mapa_puntos"), {"todos": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 52)
        self.assertFalse(response.json()["cercanos"])

    def test_mapa_filtra_clientes_segun_los_limites_visibles(self):
        response = self.client.get(
            reverse("clientes_mapa_puntos"),
            {
                "viewport": "1",
                "sur": "-17.6",
                "oeste": "-63.3",
                "norte": "-17.4",
                "este": "-63.0",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["viewport"])
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["puntos"][0]["nombre"], "Cliente lejano")

    def test_puntos_incluyen_nombre_y_id_del_responsable_actual(self):
        preventista = User.objects.create_user("responsable_mapa", password="test-password")
        preventista.perfil.rol = "preventista"
        preventista.perfil.activo = True
        preventista.perfil.save(update_fields=["rol", "activo"])
        cliente = Cliente.objects.create(
            nombres="Cliente con responsable",
            latitud=Decimal("-17.78"),
            longitud=Decimal("-63.18"),
            preventista_asignado=preventista,
        )

        response = self.client.get(reverse("clientes_mapa_puntos"), {"todos": "1"})
        punto = next(punto for punto in response.json()["puntos"] if punto["id"] == cliente.pk)

        self.assertEqual(punto["responsable_id"], preventista.pk)
        self.assertEqual(punto["responsable_nombre"], "responsable_mapa")


class TransferenciaClientesTests(TestCase):
    def setUp(self):
        self.admin = self.crear_usuario("admin", "administrador")
        self.preventista_original = self.crear_usuario("preventista1", "preventista")
        self.preventista_destino = self.crear_usuario("preventista2", "preventista")
        self.cliente = Cliente.objects.create(
            nombres="Tienda Central",
            creado_por=self.preventista_original,
            preventista_asignado=self.preventista_original,
        )
        self.pedido_historico = Pedido.objects.create(
            cliente=self.cliente,
            preventista=self.preventista_original,
            registrado_por=self.preventista_original,
        )

    @staticmethod
    def crear_usuario(username, rol):
        usuario = User.objects.create_user(username=username, password="test-password")
        perfil = usuario.perfil
        perfil.rol = rol
        perfil.activo = True
        perfil.save(update_fields=["rol", "activo"])
        return usuario

    def test_admin_transfiere_cliente_sin_cambiar_creador_ni_pedido_historico(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("transferir_clientes"),
            {
                "cliente_ids": [self.cliente.pk],
                "preventista_origen": self.preventista_original.pk,
                "preventista_destino": self.preventista_destino.pk,
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('transferir_clientes')}?origen={self.preventista_original.pk}",
        )
        self.cliente.refresh_from_db()
        self.pedido_historico.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_destino)
        self.assertEqual(self.cliente.creado_por, self.preventista_original)
        self.assertEqual(self.pedido_historico.preventista, self.preventista_original)
        self.assertEqual(TransferenciaCliente.objects.count(), 1)
        movimiento = TransferenciaCliente.objects.get()
        self.assertEqual(movimiento.responsable_anterior, self.preventista_original)
        self.assertEqual(movimiento.responsable_nuevo, self.preventista_destino)
        self.assertEqual(movimiento.realizado_por, self.admin)

    def test_admin_cambia_responsable_individual_desde_el_mapa_y_registra_historial(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("cambiar_responsable_cliente", args=[self.cliente.pk]),
            {"responsable_id": self.preventista_destino.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["cambiado"])
        self.assertEqual(response.json()["responsable_id"], self.preventista_destino.pk)
        self.assertEqual(
            response.json()["responsable_nombre"],
            self.preventista_destino.get_full_name() or self.preventista_destino.username,
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_destino)
        movimiento = TransferenciaCliente.objects.get()
        self.assertEqual(movimiento.cliente, self.cliente)
        self.assertEqual(movimiento.responsable_anterior, self.preventista_original)
        self.assertEqual(movimiento.responsable_nuevo, self.preventista_destino)
        self.assertEqual(movimiento.realizado_por, self.admin)

    def test_preventista_no_puede_cambiar_responsable_desde_el_mapa(self):
        self.client.force_login(self.preventista_original)

        response = self.client.post(
            reverse("cambiar_responsable_cliente", args=[self.cliente.pk]),
            {"responsable_id": self.preventista_destino.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_original)
        self.assertFalse(TransferenciaCliente.objects.exists())

    def test_formulario_de_cambio_de_responsable_solo_aparece_para_administrador(self):
        self.client.force_login(self.admin)
        respuesta_admin = self.client.get(reverse("clientes_mapa"))
        self.assertContains(respuesta_admin, "formCambiarResponsable")
        self.assertContains(respuesta_admin, "modalConfirmarResponsableMapa")
        self.assertContains(respuesta_admin, "Responsable actual:")

        self.client.force_login(self.preventista_original)
        respuesta_preventista = self.client.get(reverse("clientes_mapa"))
        self.assertNotContains(respuesta_preventista, "formCambiarResponsable")

    def test_cliente_transferido_sale_del_alcance_del_anterior_y_entra_al_nuevo(self):
        self.cliente.preventista_asignado = self.preventista_destino
        self.cliente.save(update_fields=["preventista_asignado"])

        self.client.force_login(self.preventista_original)
        response_anterior = self.client.get(reverse("listar_clientes"))
        self.assertNotContains(response_anterior, "Tienda Central")

        self.client.force_login(self.preventista_destino)
        response_nuevo = self.client.get(reverse("listar_clientes"))
        self.assertContains(response_nuevo, "Tienda Central")

    def test_preventista_no_puede_transferir_clientes(self):
        self.client.force_login(self.preventista_original)

        response = self.client.post(
            reverse("transferir_clientes"),
            {
                "cliente_ids": [self.cliente.pk],
                "preventista_origen": self.preventista_original.pk,
                "preventista_destino": self.preventista_destino.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_original)
        self.assertFalse(TransferenciaCliente.objects.exists())

    def test_no_muestra_carteras_hasta_elegir_el_preventista_origen(self):
        self.client.force_login(self.admin)

        response_sin_origen = self.client.get(reverse("transferir_clientes"))
        self.assertNotContains(response_sin_origen, "Tienda Central")
        self.assertContains(response_sin_origen, "Selecciona un preventista origen")

        response_con_origen = self.client.get(
            reverse("transferir_clientes"),
            {"origen": self.preventista_original.pk},
        )
        self.assertContains(response_con_origen, "Tienda Central")
        self.assertFalse(
            response_con_origen.context["preventistas_destino"]
            .filter(pk=self.preventista_original.pk)
            .exists()
        )

    def test_no_permite_incluir_cliente_de_otra_cartera_en_el_lote(self):
        otro_cliente = Cliente.objects.create(
            nombres="Otra cartera",
            creado_por=self.preventista_destino,
            preventista_asignado=self.preventista_destino,
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("transferir_clientes"),
            {
                "cliente_ids": [self.cliente.pk, otro_cliente.pk],
                "preventista_origen": self.preventista_original.pk,
                "preventista_destino": self.preventista_destino.pk,
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('transferir_clientes')}?origen={self.preventista_original.pk}",
        )
        self.assertEqual(TransferenciaCliente.objects.count(), 0)
        self.cliente.refresh_from_db()
        otro_cliente.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_original)
        self.assertEqual(otro_cliente.preventista_asignado, self.preventista_destino)

    def test_admin_puede_abrir_pantalla_y_ver_enlace_del_sidebar(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("transferir_clientes"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Transferir clientes")
        self.assertContains(response, reverse("transferir_clientes"))

    def test_pantalla_incluye_modal_de_resumen_y_recursos_de_transferencias(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("transferir_clientes"),
            {"origen": self.preventista_original.pk},
        )

        self.assertTemplateUsed(response, "transferencias/transferir.html")
        self.assertTemplateUsed(response, "transferencias/modals/confirmar.html")
        self.assertContains(response, "modalConfirmarTransferencia")
        self.assertContains(response, "Confirmar y transferir")
        self.assertContains(response, "css/transferencias/transferir.css", html=False)
        self.assertContains(response, "css/transferencias/modals/confirmar.css", html=False)
        self.assertContains(response, "js/transferencias/transferir.js", html=False)
        self.assertContains(response, "js/transferencias/modals/confirmar.js", html=False)

    def test_supervisor_conserva_acceso_a_sus_clientes_asignados_a_su_usuario(self):
        supervisor = self.crear_usuario("supervisor", "supervisor")
        cliente_supervisor = Cliente.objects.create(
            nombres="Cliente del supervisor",
            creado_por=supervisor,
            preventista_asignado=supervisor,
        )
        self.client.force_login(supervisor)

        response = self.client.get(reverse("listar_clientes"))

        self.assertContains(response, cliente_supervisor.nombres)

    def test_alta_de_preventista_se_asigna_a_si_mismo(self):
        self.client.force_login(self.preventista_destino)

        response = self.client.post(reverse("crear_cliente"), {"nombres": "Cliente Nuevo"})

        self.assertEqual(response.status_code, 302)
        cliente_nuevo = Cliente.objects.get(nombres="Cliente Nuevo")
        self.assertEqual(cliente_nuevo.creado_por, self.preventista_destino)
        self.assertEqual(cliente_nuevo.preventista_asignado, self.preventista_destino)

    def test_rechaza_destino_que_no_es_preventista(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("transferir_clientes"),
            {
                "cliente_ids": [self.cliente.pk],
                "preventista_origen": self.preventista_original.pk,
                "preventista_destino": self.admin.pk,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.preventista_asignado, self.preventista_original)
        self.assertFalse(TransferenciaCliente.objects.exists())