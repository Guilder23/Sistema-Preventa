from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0005_pedido_registrado_por"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="stock_descontado",
            field=models.BooleanField(default=False),
        ),
    ]
