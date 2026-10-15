from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0008_detallepedido_precio_ajustado"),
    ]

    operations = [
        migrations.AddField(
            model_name="detallepedido",
            name="costo_unitario",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]