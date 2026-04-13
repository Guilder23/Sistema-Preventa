from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0004_pedido_ticket_impreso_ticket_compartido"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="registrado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="pedidos_registrados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
