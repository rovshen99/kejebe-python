import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("services", "0032_attribute_schema_refactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="attribute",
            name="icon",
            field=models.FileField(
                blank=True,
                help_text="Upload an icon image (SVG/PNG/JPG/WebP recommended)",
                null=True,
                upload_to="service_attributes/icons/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["svg", "png", "jpg", "jpeg", "webp"]
                    )
                ],
                verbose_name="Icon",
            ),
        ),
    ]
