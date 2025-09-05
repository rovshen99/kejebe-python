from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0009_serviceproduct_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='favorite',
            name='service',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='services.service', verbose_name='Service'),
        ),
        migrations.AlterUniqueTogether(
            name='favorite',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='favorite',
            name='product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='services.serviceproduct', verbose_name='Product'),
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.CheckConstraint(
                name='favorite_exactly_one_target',
                check=(
                    (models.Q(('service__isnull', False)) & models.Q(('product__isnull', True)))
                    | (models.Q(('service__isnull', True)) & models.Q(('product__isnull', False)))
                ),
            ),
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.UniqueConstraint(
                fields=('user', 'service'),
                name='unique_user_service_favorite',
                condition=models.Q(('service__isnull', False)),
            ),
        ),
        migrations.AddConstraint(
            model_name='favorite',
            constraint=models.UniqueConstraint(
                fields=('user', 'product'),
                name='unique_user_product_favorite',
                condition=models.Q(('product__isnull', False)),
            ),
        ),
    ]

