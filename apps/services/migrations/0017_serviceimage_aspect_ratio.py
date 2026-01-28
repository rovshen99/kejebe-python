from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0016_service_is_vip"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceimage",
            name="aspect_ratio",
            field=models.FloatField(blank=True, null=True, verbose_name="Aspect Ratio"),
        ),
    ]
