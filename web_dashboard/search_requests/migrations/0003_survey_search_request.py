# Generated by Django 5.0.3 on 2024-04-06 09:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search_requests', '0002_delete_surveysearchrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='search_request',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='search_requests.searchrequest'),
            preserve_default=False,
        ),
    ]
