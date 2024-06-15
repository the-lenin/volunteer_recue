# Generated by Django 5.0.6 on 2024-06-15 18:39

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_customuser_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='dateofbirth',
            field=models.DateField(default=datetime.datetime(2024, 6, 15, 18, 39, 33, 721257), verbose_name='Date of birth'),
            preserve_default=False,
        ),
    ]
