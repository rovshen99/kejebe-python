from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0023_alter_contacttype_icon_filefield"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicevideo",
            name="preview",
            field=models.ImageField(blank=True, null=True, upload_to="services/videos/previews", verbose_name="Preview image"),
        ),
    ]
