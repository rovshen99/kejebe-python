from django.db import migrations, models


def forwards_fill_open_fields(apps, schema_editor):
    Banner = apps.get_model("banners", "Banner")
    for banner in Banner.objects.all():
        if getattr(banner, "open_type", None):
            continue
        if getattr(banner, "service_id", None):
            banner.open_type = "service"
            banner.open_params = {"service_id": banner.service_id}
            banner.save(update_fields=["open_type", "open_params"])
            continue
        link_url = getattr(banner, "link_url", None)
        if link_url:
            banner.open_type = "url"
            banner.open_params = {"url": link_url}
            banner.save(update_fields=["open_type", "open_params"])


class Migration(migrations.Migration):

    dependencies = [
        ("banners", "0002_banner_service_alter_banner_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="banner",
            name="open_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("service", "Service"),
                    ("search", "Search"),
                    ("navigate", "Navigate"),
                    ("url", "URL"),
                ],
                max_length=20,
                null=True,
                verbose_name="Open Type",
            ),
        ),
        migrations.AddField(
            model_name="banner",
            name="open_params",
            field=models.JSONField(blank=True, default=dict, verbose_name="Open Params"),
        ),
        migrations.RunPython(forwards_fill_open_fields, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="banner",
            name="link_url",
        ),
        migrations.RemoveField(
            model_name="banner",
            name="service",
        ),
    ]
