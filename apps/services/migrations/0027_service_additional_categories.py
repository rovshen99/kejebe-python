from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0004_remove_category_name_en"),
        ("services", "0026_alter_servicevideo_preview"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="additional_categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="services_additional",
                to="categories.category",
                verbose_name="Additional Categories",
            ),
        ),
    ]
