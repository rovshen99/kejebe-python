from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0023_remove_systemcontact"),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceapplication",
            name="category_name",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="Category Name"),
        ),
        migrations.AddField(
            model_name="serviceapplication",
            name="city_name",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="City Name"),
        ),
        migrations.AlterField(
            model_name="serviceapplication",
            name="city",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="regions.city", verbose_name="City"),
        ),
    ]
