from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.pedidos.models import (
    DevolucionItem,
    DevolucionPedido,
    DetallePedido,
    Pedido,
)
from apps.productos.models import Producto


class ReporteUtilidadTests(TestCase):
    def setUp(self):
        self.admin = self.crear_usuario("admin_utilidad", "administrador")
        self.preventista = self.crear_usuario("preventista_utilidad", "preventista")
        self.otro_preventista = self.crear_usuario("preventista_otro", "preventista")
        self.repartidor = self.crear_usuario("repartidor_utilidad", "repartidor")
        self.preventista.perfil.repartidor = self.repartidor
        self.preventista.perfil.save(update_fields=["repartidor"])
        self.cliente = Cliente.objects.create(
            nombres="Tienda Utilidad",
            creado_por=self.preventista,
            preventista_asignado=self.preventista,
        )
        self.producto = Producto.objects.create(
            codigo="UTIL-01",
            nombre="Producto de prueba",
            precio_unidad=Decimal("100.00"),
            precio_compra_unidad=Decimal("60.00"),
            stock_unidades=20,
        )

    @staticmethod
    def crear_usuario(username, rol):
        usuario = User.objects.create_user(username=username, password="test-password")
        perfil = usuario.perfil
        perfil.rol = rol
        perfil.activo = True
        perfil.save(update_fields=["rol", "activo"])
        return usuario

    def crear_pedido_vendido(
        self,
        preventista,
        fecha_venta,
        *,
        cantidad=1,
        precio=Decimal("100.00"),
        costo=Decimal("60.00"),
    ):
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            preventista=preventista,
            estado=Pedido.ESTADO_VENDIDO,
            fecha_vendido=timezone.make_aware(datetime.combine(fecha_venta, time(12, 0))),
            total=precio * cantidad,
        )
        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=cantidad,
            precio_unitario=precio,
            costo_unitario=costo,
            subtotal=precio * cantidad,
        )
        return pedido

    def test_costo_y_utilidad_consideran_unidades_devuelta_aunque_no_repuesta(self):
        self.producto.precio_unidad = Decimal("2.00")
        self.producto.precio_compra_unidad = Decimal("1.00")
        self.producto.save(update_fields=["precio_unidad", "precio_compra_unidad"])
        self.client.force_login(self.preventista)
        fecha_entrega = (timezone.localdate() + timedelta(days=1)).isoformat()

        response = self.client.post(
            reverse("crear_pedido"),
            {
                "cliente_id": self.cliente.pk,
                "fecha_entrega_estimada": fecha_entrega,
                "producto_id[]": [self.producto.pk],
                "cantidad[]": [10],
            },
        )

        self.assertEqual(response.status_code, 302)
        pedido = Pedido.objects.get(cliente=self.cliente)
        detalle = pedido.detalles.get()
        self.assertEqual(detalle.precio_unitario, Decimal("2.00"))
        self.assertEqual(detalle.costo_unitario, Decimal("1.00"))

        pedido.estado = Pedido.ESTADO_VENDIDO
        pedido.fecha_vendido = timezone.now()
        pedido.save(update_fields=["estado", "fecha_vendido"])
        self.producto.precio_unidad = Decimal("150.00")
        self.producto.precio_compra_unidad = Decimal("90.00")
        self.producto.save(update_fields=["precio_unidad", "precio_compra_unidad"])

        devolucion = DevolucionPedido.objects.create(
            pedido=pedido,
            repartidor=self.admin,
            tipo=DevolucionPedido.TIPO_PARCIAL,
        )
        DevolucionItem.objects.create(
            devolucion=devolucion,
            detalle_pedido=detalle,
            producto=self.producto,
            cantidad_devuelta=5,
            repuesto=False,
        )

        response = self.client.get(reverse("reporte_utilidad"), {"periodo": "dia"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["venta_neta_total"], Decimal("10.00"))
        self.assertEqual(response.context["costo_total"], Decimal("5.00"))
        self.assertEqual(response.context["utilidad_total"], Decimal("5.00"))
        self.assertEqual(response.context["pedidos_con_costo"], 1)
        self.assertEqual(response.context["pedidos_sin_costo"], 0)

    def test_pedidos_sin_costo_historico_no_inflan_utilidad_y_rango_filtra_vendedor(self):
        hoy = timezone.localdate()
        pedido_con_costo = self.crear_pedido_vendido(self.preventista, hoy)
        pedido_sin_costo = self.crear_pedido_vendido(
            self.preventista,
            hoy,
            precio=Decimal("80.00"),
            costo=None,
        )
        self.crear_pedido_vendido(self.otro_preventista, hoy)
        ayer = hoy - timedelta(days=1)
        self.crear_pedido_vendido(self.preventista, ayer)

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("reporte_utilidad"),
            {
                "periodo": "personalizado",
                "desde": hoy.isoformat(),
                "hasta": hoy.isoformat(),
                "preventista": self.preventista.pk,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_pedidos"], 2)
        self.assertEqual(response.context["pedidos_con_costo"], 1)
        self.assertEqual(response.context["pedidos_sin_costo"], 1)
        self.assertEqual(response.context["venta_neta_total"], Decimal("180.00"))
        self.assertEqual(response.context["venta_con_costo"], Decimal("100.00"))
        self.assertEqual(response.context["costo_total"], Decimal("60.00"))
        self.assertEqual(response.context["utilidad_total"], Decimal("40.00"))

    def test_periodos_rapidos_y_rango_invalido(self):
        hoy = timezone.localdate()
        self.crear_pedido_vendido(self.preventista, hoy)
        self.crear_pedido_vendido(self.preventista, hoy - timedelta(days=1))
        self.client.force_login(self.admin)

        for periodo in ("dia", "semana", "mes"):
            with self.subTest(periodo=periodo):
                response = self.client.get(reverse("reporte_utilidad"), {"periodo": periodo})
                self.assertEqual(response.status_code, 200)
                self.assertGreaterEqual(response.context["total_pedidos"], 1)

        response = self.client.get(
            reverse("reporte_utilidad"),
            {"periodo": "personalizado", "desde": hoy.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("fecha de inicio y una fecha de fin", response.context["error_fechas"])
        self.assertEqual(response.context["total_pedidos"], 0)

        response = self.client.get(
            reverse("reporte_utilidad"),
            {
                "periodo": "personalizado",
                "desde": "2026-02-31",
                "hasta": "2026-03-01",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["error_fechas"])
        self.assertEqual(response.context["total_pedidos"], 0)

    def test_pedidos_pendientes_anulados_y_no_entregados_no_cuentan_como_venta(self):
        hoy = timezone.localdate()
        for estado in (
            Pedido.ESTADO_PENDIENTE,
            Pedido.ESTADO_ANULADO,
            Pedido.ESTADO_NO_ENTREGADO,
        ):
            pedido = self.crear_pedido_vendido(self.preventista, hoy)
            pedido.estado = estado
            pedido.save(update_fields=["estado"])

        self.client.force_login(self.admin)
        response = self.client.get(reverse("reporte_utilidad"), {"periodo": "dia"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_pedidos"], 0)
        self.assertEqual(response.context["venta_neta_total"], Decimal("0.00"))
        self.assertEqual(response.context["costo_total"], Decimal("0.00"))
        self.assertEqual(response.context["utilidad_total"], Decimal("0.00"))

    def test_entrega_parcial_sin_unidades_no_cambia_pedido_a_vendido(self):
        pedido = Pedido.objects.create(
            cliente=self.cliente,
            preventista=self.preventista,
            estado=Pedido.ESTADO_PENDIENTE,
            total=Decimal("20.00"),
        )
        detalle = DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=10,
            precio_unitario=Decimal("2.00"),
            costo_unitario=Decimal("1.00"),
            subtotal=Decimal("20.00"),
        )
        self.client.force_login(self.repartidor)

        response = self.client.post(
            reverse("registrar_entrega_pedido", args=[pedido.pk]),
            {
                "resultado": "entregado_parcial",
                f"cantidad_entregada_{detalle.pk}": "0",
            },
        )

        self.assertRedirects(response, reverse("listar_pedidos"))
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.ESTADO_PENDIENTE)
        self.assertFalse(DevolucionPedido.objects.filter(pedido=pedido).exists())

    def test_utilidad_aparece_como_pestana_junto_a_devoluciones(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("reportes_inicio"))
        utilidad_response = self.client.get(reverse("reporte_utilidad"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Devoluciones")
        self.assertContains(response, reverse("reporte_utilidad"))
        self.assertNotContains(utilidad_response, "Aplicar filtros")
        self.assertContains(utilidad_response, "utilidad-totals", html=False)
        self.assertContains(utilidad_response, 'aria-label="Descargar reporte PDF"', html=False)

    def test_descarga_pdf_respeta_filtro_y_entrega_archivo_pdf(self):
        self.crear_pedido_vendido(self.preventista, timezone.localdate())
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("reporte_utilidad"),
            {"periodo": "dia", "preventista": self.preventista.pk, "formato": "pdf"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("reporte_utilidad.pdf", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))