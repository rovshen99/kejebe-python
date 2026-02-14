from django.db import migrations, models
import django.db.models.deletion


def copy_system_contacts(apps, schema_editor):
    connection = schema_editor.connection
    if "services_systemcontact" not in connection.introspection.table_names():
        return
    OldContact = apps.get_model("services", "SystemContact")
    NewContact = apps.get_model("system", "SystemContact")
    db_alias = schema_editor.connection.alias
    to_create = []
    for item in OldContact.objects.using(db_alias).all():
        to_create.append(
            NewContact(
                type_id=item.type_id,
                value=item.value,
                is_active=item.is_active,
                priority=item.priority,
            )
        )
    if to_create:
        NewContact.objects.using(db_alias).bulk_create(to_create)


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0022_system_contact"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(max_length=255, verbose_name="Contact Value")),
                ("is_active", models.BooleanField(default=True, verbose_name="Is Active")),
                ("priority", models.PositiveIntegerField(default=100, verbose_name="Priority")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                (
                    "type",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="system_contacts",
                        to="services.contacttype",
                        verbose_name="Contact Type",
                    ),
                ),
            ],
            options={
                "verbose_name": "System Contact",
                "verbose_name_plural": "System Contacts",
                "ordering": ("priority", "id"),
            },
        ),
        migrations.RunPython(copy_system_contacts, migrations.RunPython.noop),
    ]
