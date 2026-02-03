from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("regions", "0002_city_is_region_level"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="region",
            name="name_en",
        ),
        migrations.RemoveField(
            model_name="city",
            name="name_en",
        ),
    ]
