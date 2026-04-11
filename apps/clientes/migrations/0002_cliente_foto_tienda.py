from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="foto_tienda",
            field=models.ImageField(blank=True, null=True, upload_to="clientes/tiendas/"),
        ),
    ]
