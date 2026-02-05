from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("banners", "0004_remove_banner_title_en"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="banner",
            index=models.Index(fields=["is_active", "starts_at", "ends_at"], name="banner_active_range_idx"),
        ),
        migrations.AddIndex(
            model_name="banner",
            index=models.Index(fields=["priority", "created_at"], name="banner_priority_created_idx"),
        ),
    ]
