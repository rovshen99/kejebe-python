from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0018_alter_service_description_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="service",
            name="title_en",
        ),
        migrations.RemoveField(
            model_name="service",
            name="description_en",
        ),
        migrations.RemoveField(
            model_name="contacttype",
            name="name_en",
        ),
        migrations.RemoveField(
            model_name="servicetag",
            name="name_en",
        ),
        migrations.RemoveField(
            model_name="attribute",
            name="name_en",
        ),
        migrations.RemoveField(
            model_name="attributevalue",
            name="value_text_en",
        ),
        migrations.RemoveField(
            model_name="serviceproduct",
            name="title_en",
        ),
        migrations.RemoveField(
            model_name="serviceproduct",
            name="description_en",
        ),
    ]
