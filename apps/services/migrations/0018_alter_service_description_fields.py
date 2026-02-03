from django.db import migrations
import django_summernote.fields


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0017_serviceimage_aspect_ratio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="service",
            name="description_tm",
            field=django_summernote.fields.SummernoteTextField(verbose_name="Description (TM)"),
        ),
        migrations.AlterField(
            model_name="service",
            name="description_ru",
            field=django_summernote.fields.SummernoteTextField(verbose_name="Description (RU)"),
        ),
        migrations.AlterField(
            model_name="service",
            name="description_en",
            field=django_summernote.fields.SummernoteTextField(verbose_name="Description (EN)"),
        ),
    ]
