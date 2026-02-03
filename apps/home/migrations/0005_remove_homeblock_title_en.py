from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0004_homepageconfig_region"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="homeblock",
            name="title_en",
        ),
    ]
