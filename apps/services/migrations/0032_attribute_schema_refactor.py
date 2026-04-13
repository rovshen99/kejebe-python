# Generated manually on 2026-04-08

import django.db.models.deletion
from django.db import migrations, models


def seed_category_attributes_from_legacy_attribute_category(apps, schema_editor):
    Attribute = apps.get_model("services", "Attribute")
    CategoryAttribute = apps.get_model("services", "CategoryAttribute")

    rows = []
    for attribute in Attribute.objects.exclude(category_id__isnull=True).iterator():
        rows.append(
            CategoryAttribute(
                category_id=attribute.category_id,
                attribute_id=attribute.id,
                scope="product",
                is_required=attribute.is_required,
                is_filterable=False,
                is_highlighted=False,
                section_tm="",
                section_ru="",
                show_in_filters=False,
                show_in_card=False,
                show_in_detail=True,
                filter_type="auto",
                filter_order=100,
                sort_order=100,
            )
        )

    if rows:
        CategoryAttribute.objects.bulk_create(rows, ignore_conflicts=True)


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):

    dependencies = [
        ("categories", "0004_remove_category_name_en"),
        ("services", "0031_vendor_cabinet_status_and_media_positions"),
    ]

    operations = [
        migrations.CreateModel(
            name="AttributeOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.SlugField(max_length=100, verbose_name="Value")),
                ("label_tm", models.CharField(max_length=100, verbose_name="Label (TM)")),
                ("label_ru", models.CharField(max_length=100, verbose_name="Label (RU)")),
                ("sort_order", models.PositiveIntegerField(default=100, verbose_name="Sort Order")),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
            ],
            options={
                "verbose_name": "Attribute Option",
                "verbose_name_plural": "Attribute Options",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.CreateModel(
            name="CategoryAttribute",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "scope",
                    models.CharField(
                        choices=[("service", "Service"), ("product", "Product")],
                        max_length=16,
                        verbose_name="Scope",
                    ),
                ),
                ("is_required", models.BooleanField(default=False, verbose_name="Is Required")),
                ("is_filterable", models.BooleanField(default=False, verbose_name="Is Filterable")),
                ("is_highlighted", models.BooleanField(default=False, verbose_name="Is Highlighted")),
                ("section_tm", models.CharField(blank=True, default="", max_length=100, verbose_name="Section (TM)")),
                ("section_ru", models.CharField(blank=True, default="", max_length=100, verbose_name="Section (RU)")),
                ("show_in_filters", models.BooleanField(default=False, verbose_name="Show in Filters")),
                ("show_in_card", models.BooleanField(default=False, verbose_name="Show in Card")),
                ("show_in_detail", models.BooleanField(default=True, verbose_name="Show in Detail")),
                (
                    "filter_type",
                    models.CharField(
                        choices=[
                            ("auto", "Auto"),
                            ("checkbox", "Checkbox"),
                            ("select", "Select"),
                            ("multiselect", "Multi Select"),
                            ("range", "Range"),
                        ],
                        default="auto",
                        max_length=20,
                        verbose_name="Filter Type",
                    ),
                ),
                ("filter_order", models.PositiveIntegerField(default=100, verbose_name="Filter Order")),
                ("sort_order", models.PositiveIntegerField(default=100, verbose_name="Sort Order")),
            ],
            options={
                "verbose_name": "Category Attribute",
                "verbose_name_plural": "Category Attributes",
                "ordering": ("sort_order", "id"),
            },
        ),
        migrations.CreateModel(
            name="ServiceAttributeValue",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value_text_tm", models.CharField(blank=True, max_length=100, null=True, verbose_name="Text Value (TM)")),
                ("value_text_ru", models.CharField(blank=True, max_length=100, null=True, verbose_name="Text Value (RU)")),
                ("value_number", models.FloatField(blank=True, null=True, verbose_name="Number Value")),
                ("value_boolean", models.BooleanField(blank=True, null=True, verbose_name="Boolean Value")),
            ],
            options={
                "verbose_name": "Service Attribute Value",
                "verbose_name_plural": "Service Attribute Values",
            },
        ),
        migrations.RenameModel(
            old_name="AttributeValue",
            new_name="ProductAttributeValue",
        ),
        migrations.AlterModelOptions(
            name="attribute",
            options={"ordering": ("name_tm", "id"), "verbose_name": "Attribute", "verbose_name_plural": "Attributes"},
        ),
        migrations.AlterModelOptions(
            name="productattributevalue",
            options={"verbose_name": "Product Attribute Value", "verbose_name_plural": "Product Attribute Values"},
        ),
        migrations.AlterUniqueTogether(
            name="attribute",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="productattributevalue",
            unique_together=set(),
        ),
        migrations.AddField(
            model_name="attribute",
            name="help_text_ru",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Help Text (RU)"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="icon",
            field=models.FileField(
                blank=True,
                help_text="Upload an icon image (SVG/PNG/JPG/WebP recommended)",
                null=True,
                upload_to="service_attributes/icons/",
                validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["svg", "png", "jpg", "jpeg", "webp"])],
                verbose_name="Icon",
            ),
        ),
        migrations.AddField(
            model_name="attribute",
            name="help_text_tm",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Help Text (TM)"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Is Active"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="max_value",
            field=models.FloatField(blank=True, null=True, verbose_name="Max Value"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="min_value",
            field=models.FloatField(blank=True, null=True, verbose_name="Min Value"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="placeholder_ru",
            field=models.CharField(blank=True, default="", max_length=150, verbose_name="Placeholder (RU)"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="placeholder_tm",
            field=models.CharField(blank=True, default="", max_length=150, verbose_name="Placeholder (TM)"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="step",
            field=models.FloatField(blank=True, null=True, verbose_name="Step"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="unit_ru",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="Unit (RU)"),
        ),
        migrations.AddField(
            model_name="attribute",
            name="unit_tm",
            field=models.CharField(blank=True, default="", max_length=32, verbose_name="Unit (TM)"),
        ),
        migrations.AlterField(
            model_name="attribute",
            name="input_type",
            field=models.CharField(
                choices=[
                    ("text", "Text"),
                    ("number", "Number"),
                    ("boolean", "Boolean"),
                    ("choice", "Choice"),
                    ("multiselect", "Multi Select"),
                ],
                db_index=True,
                max_length=20,
                verbose_name="Input Type",
            ),
        ),
        migrations.AlterField(
            model_name="productattributevalue",
            name="value_text_ru",
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="Text Value (RU)"),
        ),
        migrations.AlterField(
            model_name="productattributevalue",
            name="value_text_tm",
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="Text Value (TM)"),
        ),
        migrations.AddField(
            model_name="attributeoption",
            name="attribute",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="options",
                to="services.attribute",
                verbose_name="Attribute",
            ),
        ),
        migrations.AddField(
            model_name="productattributevalue",
            name="option",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="services.attributeoption",
                verbose_name="Option",
            ),
        ),
        migrations.AddField(
            model_name="categoryattribute",
            name="attribute",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="category_links",
                to="services.attribute",
                verbose_name="Attribute",
            ),
        ),
        migrations.AddField(
            model_name="categoryattribute",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="category_attributes",
                to="categories.category",
                verbose_name="Category",
            ),
        ),
        migrations.AddField(
            model_name="serviceattributevalue",
            name="attribute",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="services.attribute",
                verbose_name="Attribute",
            ),
        ),
        migrations.AddField(
            model_name="serviceattributevalue",
            name="option",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="services.attributeoption",
                verbose_name="Option",
            ),
        ),
        migrations.AddField(
            model_name="serviceattributevalue",
            name="service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="service_attribute_values",
                to="services.service",
                verbose_name="Service",
            ),
        ),
        migrations.RunPython(seed_category_attributes_from_legacy_attribute_category, noop_reverse),
        migrations.RemoveField(
            model_name="attribute",
            name="category",
        ),
        migrations.AddConstraint(
            model_name="attributeoption",
            constraint=models.UniqueConstraint(fields=("attribute", "value"), name="uniq_attribute_option_value"),
        ),
        migrations.AddConstraint(
            model_name="categoryattribute",
            constraint=models.UniqueConstraint(
                fields=("category", "attribute", "scope"),
                name="uniq_category_attribute_scope",
            ),
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("option__isnull", True)),
                fields=("product", "attribute"),
                name="uniq_product_attr_without_option",
            ),
        ),
        migrations.AddConstraint(
            model_name="productattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("option__isnull", False)),
                fields=("product", "attribute", "option"),
                name="uniq_product_attr_with_option",
            ),
        ),
        migrations.AddConstraint(
            model_name="serviceattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("option__isnull", True)),
                fields=("service", "attribute"),
                name="uniq_service_attr_without_option",
            ),
        ),
        migrations.AddConstraint(
            model_name="serviceattributevalue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("option__isnull", False)),
                fields=("service", "attribute", "option"),
                name="uniq_service_attr_with_option",
            ),
        ),
    ]
