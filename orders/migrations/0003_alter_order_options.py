# Generated by Django 4.2.3 on 2023-07-15 22:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0002_order_stripe_id_alter_order_address_alter_order_city_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created'], 'verbose_name': 'Заказ', 'verbose_name_plural': 'Заказы'},
        ),
    ]
