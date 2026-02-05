from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0020_alter_service_available_cities"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="service",
            index=models.Index(fields=["is_active", "priority", "created_at"], name="service_active_order_idx"),
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(fields=["category", "is_active"], name="service_category_active_idx"),
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(fields=["city", "is_active"], name="service_city_active_idx"),
        ),
    ]
