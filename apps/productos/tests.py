from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Producto


class ProductoMoneyPrecisionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Password123",
        )
        self.client.force_login(self.admin)

    def test_crear_producto_guarda_precio_exacto_con_dos_decimales(self):
        response = self.client.post(
            reverse("crear_producto"),
            {
                "codigo": "P001",
                "nombre": "Producto 1",
                "descripcion": "Demo",
                "precio_unidad": "40",
                "precio_caja": "40",
                "precio_compra_unidad": "40",
                "precio_compra_caja": "40",
                "stock_umbral_amarillo": "10",
                "stock_umbral_rojo": "3",
            },
        )

        self.assertRedirects(response, reverse("listar_productos"))
        producto = Producto.objects.get(codigo="P001")
        self.assertEqual(producto.precio_unidad, Decimal("40.00"))
        self.assertEqual(producto.precio_caja, Decimal("40.00"))
        self.assertEqual(producto.precio_compra_unidad, Decimal("40.00"))
        self.assertEqual(producto.precio_compra_caja, Decimal("40.00"))

    def test_editar_producto_conserva_precio_exacto(self):
        producto = Producto.objects.create(
            codigo="P002",
            nombre="Producto 2",
            precio_unidad=Decimal("10.00"),
            precio_caja=Decimal("20.00"),
            precio_compra_unidad=Decimal("30.00"),
            precio_compra_caja=Decimal("40.00"),
        )

        response = self.client.post(
            reverse("editar_producto", args=[producto.id]),
            {
                "nombre": "Producto 2 editado",
                "descripcion": "",
                "precio_unidad": "40",
                "precio_caja": "40",
                "precio_compra_unidad": "40",
                "precio_compra_caja": "40",
                "stock_umbral_amarillo": "10",
                "stock_umbral_rojo": "3",
                "activo": "on",
            },
        )

        self.assertRedirects(response, reverse("listar_productos"))
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Producto 2 editado")
        self.assertEqual(producto.precio_unidad, Decimal("40.00"))
        self.assertEqual(producto.precio_caja, Decimal("40.00"))
        self.assertEqual(producto.precio_compra_unidad, Decimal("40.00"))
        self.assertEqual(producto.precio_compra_caja, Decimal("40.00"))

    def test_inventario_devuelve_precio_compra_formateado_exacto(self):
        producto = Producto.objects.create(
            codigo="P003",
            nombre="Producto 3",
            precio_compra_unidad=Decimal("40.00"),
            stock_unidades=2,
        )

        response = self.client.get(reverse("obtener_inventario_producto", args=[producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "id": producto.id,
                "codigo": "P003",
                "nombre": "Producto 3",
                "stock_actual": 2,
                "precio_compra_unidad": "40.00",
                "valor_inventario_compra": "80.00",
                "movimientos": [],
            },
        )
