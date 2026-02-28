from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("system", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountDeletionRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("phone", models.CharField(db_index=True, max_length=32, verbose_name="Phone Number")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("processed", "Processed")],
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
            ],
            options={
                "verbose_name": "Account Deletion Request",
                "verbose_name_plural": "Account Deletion Requests",
                "ordering": ("-created_at",),
            },
        ),
    ]
