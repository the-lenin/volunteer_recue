# Generated by Django 5.0.6 on 2024-05-24 13:44

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0010_remove_crew_members_crew_passengers'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='crew',
            name='passengers',
            field=models.ManyToManyField(blank=True, null=True, related_name='passenger_crews', to=settings.AUTH_USER_MODEL, verbose_name='Passangers'),
        ),
    ]
