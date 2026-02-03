from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("banners", "0003_banner_open_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="banner",
            name="title_en",
        ),
    ]
