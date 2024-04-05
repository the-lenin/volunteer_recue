# Generated by Django 5.0.3 on 2024-04-05 09:42

import django.contrib.gis.geos.point
import django.db.models.deletion
import location_field.models.spatial
import phonenumber_field.modelfields
import web_dashboard.search_requests.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SearchRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(help_text='Required 128 characters or fewer.', max_length=128, verbose_name='Full name')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='Date of birth')),
                ('age', models.CharField(choices=[('CHLD', 'Child'), ('TNGR', 'Teenager'), ('ADLT', 'Adult'), ('OLDR', 'Olderly')], default='ADLT', max_length=4, verbose_name='Age')),
                ('sex', models.CharField(choices=[('M', 'Male'), ('F', 'Female'), ('U', 'Unspecified')], default='U', max_length=1, verbose_name='Sex')),
                ('location', location_field.models.spatial.LocationField(default=django.contrib.gis.geos.point.Point(82.919782, 55.029738), srid=4326, verbose_name='Location')),
                ('city', models.CharField(help_text='Type a city name to find coordinates on map', max_length=255, verbose_name='City')),
                ('disappearance_date', models.DateField(verbose_name='Disappearnce Date')),
                ('circumstances', models.TextField(blank=True, null=True, verbose_name='Circumstances of disapprance')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None, verbose_name='Phone number')),
                ('internet_data', models.TextField(blank=True, null=True, verbose_name='Internet Data')),
                ('features', models.TextField(verbose_name='Features')),
                ('clothing', models.TextField(verbose_name='Clothing')),
                ('personal_belongings', models.TextField(verbose_name='Personal Belongings')),
                ('photos', models.ImageField(blank=True, null=True, upload_to=web_dashboard.search_requests.models.path_and_rename, verbose_name='Photos')),
                ('health_condition', models.TextField(verbose_name='Health condition')),
                ('alcohol', models.BooleanField(default=False, verbose_name='Alcohol')),
                ('drugs', models.BooleanField(default=False, verbose_name='Drugs')),
                ('additional_info', models.TextField(blank=True, null=True, verbose_name='Additional Information')),
                ('reporter_full_name', models.CharField(help_text='Required 128 characters or fewer.', max_length=128, verbose_name='Reporter full name')),
                ('reporter_contact_details', models.TextField(verbose_name='Reporter contact details')),
                ('reporter_relationship', models.CharField(help_text='Required 128 characters or fewer.', max_length=128, verbose_name='Reporter relationship to missing person')),
                ('reporter_has_reported_to_police', models.BooleanField(default=False, verbose_name='Has reporter reported to police')),
                ('status', models.CharField(choices=[('O', 'Open'), ('A', 'Active'), ('C', 'Closed')], default='O', max_length=1, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
            ],
        ),
        migrations.CreateModel(
            name='Survey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(help_text='Required 64 characters or fewer.', max_length=64, verbose_name='First name')),
                ('last_name', models.CharField(help_text='Required 64 characters or fewer.', max_length=64, verbose_name='Last name')),
                ('patronymic_name', models.CharField(blank=True, help_text='Required 64 characters or fewer.', max_length=64, null=True, verbose_name='Patronymic name')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None, verbose_name='Phone number')),
                ('relationship', models.CharField(help_text='Required 32 characters or fewer.', max_length=32, verbose_name='Relationship')),
                ('additiona_info', models.TextField(blank=True, null=True, verbose_name='Additional information')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
            ],
        ),
        migrations.CreateModel(
            name='SurveySearchRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('search_request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='surveys', to='search_requests.searchrequest', verbose_name='Search Request')),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='search_requests', to='search_requests.survey', verbose_name='Survey')),
            ],
        ),
    ]
