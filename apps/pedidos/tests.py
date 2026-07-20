from datetime import date, datetime, timezone

from django.test import SimpleTestCase
from django.utils import timezone as django_timezone

from apps.pedidos.views import _formatear_fecha_local_pedido, _formatear_hora_local
from apps.reportes.views import _formatear_fecha_hora_local


class FormatoHoraLocalTests(SimpleTestCase):
    def test_formato_usa_hora_de_bolivia(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        with django_timezone.override("America/La_Paz"):
            self.assertEqual(_formatear_hora_local(dt), "01/01/2024 08:00")

    def test_formato_de_reporte_usa_hora_local(self):
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        with django_timezone.override("America/La_Paz"):
            self.assertEqual(_formatear_fecha_hora_local(dt), "01/01/2024 08:00")

    def test_formato_de_fecha_sin_hora_no_rompe(self):
        dt = date(2024, 1, 1)

        self.assertEqual(_formatear_fecha_local_pedido(dt), "01/01/2024")
