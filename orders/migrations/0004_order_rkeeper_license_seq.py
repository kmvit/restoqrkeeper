# Generated by Django 5.2 on 2025-05-07 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_order_station_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='rkeeper_license_seq',
            field=models.IntegerField(default=0, verbose_name='SeqNumber лицензирования'),
        ),
    ]
