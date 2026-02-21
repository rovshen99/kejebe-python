from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0022_serviceapplication_category_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contacttype",
            name="icon",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="contact_type_icons/",
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=["svg", "png", "jpg", "jpeg", "webp"]
                    )
                ],
                verbose_name="Icon",
                help_text="Upload an icon image (SVG/PNG/JPG/WebP recommended)",
            ),
        ),
    ]
