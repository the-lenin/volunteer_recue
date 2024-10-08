# Generated by Django 5.0.6 on 2024-06-14 13:00

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logistics', '0016_alter_crew_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='JoinRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_time', models.DateTimeField(auto_now_add=True, verbose_name='Request Time')),
                ('status', models.CharField(choices=[('P', 'Pending'), ('A', 'Accepted'), ('R', 'Rejected')], default='P', max_length=1, verbose_name='status')),
                ('crew', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='join_requests', to='logistics.crew', verbose_name='Crew')),
                ('passenger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='join_requests', to=settings.AUTH_USER_MODEL, verbose_name='Passenger')),
            ],
            options={
                'unique_together': {('passenger', 'crew')},
            },
        ),
    ]
