from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0003_category_icon_crop_applied_category_icon_cropping_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="category",
            name="name_en",
        ),
    ]
