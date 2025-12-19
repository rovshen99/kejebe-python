from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0003_alter_homeblock_source_mode"),
        ("regions", "0002_city_is_region_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="homepageconfig",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="home_configs",
                to="regions.region",
            ),
        ),
    ]
