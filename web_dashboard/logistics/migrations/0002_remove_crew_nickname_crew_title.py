# Generated by Django 5.0.3 on 2024-04-13 09:32

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='crew',
            name='nickname',
        ),
        migrations.AddField(
            model_name='crew',
            name='title',
            field=models.CharField(default=django.utils.timezone.now, help_text='Required 32 characters or fewer.', max_length=32, verbose_name='Title'),
            preserve_default=False,
        ),
    ]
