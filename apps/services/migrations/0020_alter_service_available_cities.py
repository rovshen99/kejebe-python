from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0019_remove_en_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="available_cities",
            field=models.ManyToManyField(blank=True, related_name="services", to="regions.city", verbose_name="Available Cities"),
        ),
    ]
