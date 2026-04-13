from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0003_alter_pedido_estado_devolucionpedido_devolucionitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="ticket_compartido",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="pedido",
            name="ticket_impreso",
            field=models.BooleanField(default=False),
        ),
    ]
