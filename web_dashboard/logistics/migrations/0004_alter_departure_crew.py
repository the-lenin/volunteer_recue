# Generated by Django 5.0.3 on 2024-04-18 08:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0003_remove_task_search_request_departure_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='departure',
            name='crew',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='logistics.crew', verbose_name='Crew'),
        ),
    ]
