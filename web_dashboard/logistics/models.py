from django.db import models
from django.core import serializers
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import Point
from phonenumber_field.modelfields import PhoneNumberField
from location_field.models.spatial import LocationField

from web_dashboard.users.models import CustomUser
from web_dashboard.search_requests.models import GetFieldsMixin
from web_dashboard.search_requests import models as models_sr


class Departure(GetFieldsMixin, models.Model):
    """Class represents departure."""
    search_request = models.ForeignKey(
        models_sr.SearchRequest,
        related_name='departures',
        verbose_name=_('Search Request'),
        on_delete=models.CASCADE
    )

    class StatusVerbose(models.TextChoices):
        """Search request status choices."""
        OPEN = 'O', _('Open')
        ACTIVE = 'A', _('Active')
        CLOSED = 'C', _('Closed')

    status = models.CharField(
        _('Status'),
        max_length=1,
        choices=StatusVerbose.choices,
        default=StatusVerbose.OPEN,
    )

    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )

    def __str__(self) -> str:
        """Representation of a single instance."""
        return f'ID {self.id} ({self.get_status_display()})'

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('logistics:read', kwargs={'pk': self.pk})


class Crew(GetFieldsMixin, models.Model):
    """Class represent crew."""
    departure = models.ForeignKey(
        Departure,
        related_name='crews',
        verbose_name=_('Departure'),
        on_delete=models.CASCADE,
    )

    class StatusVerbose(models.TextChoices):
        """Crew status choices."""
        AVAILABLE = 'A', _('Available')
        ON_MISSION = 'M', _('On mission')
        RETURNING = 'R', _('Returning')

    status = models.CharField(
        _('status'),
        max_length=1,
        choices=StatusVerbose.choices,
        default=StatusVerbose.AVAILABLE,
    )

    departure_datetime = models.DateTimeField(
        _('Departure at'),
        blank=True,
        null=True,
    )

    return_datetime = models.DateTimeField(
        _('Return at'),
        blank=True,
        null=True,
    )

    title = models.CharField(
        _('Title'),
        max_length=32,
        help_text=_("Required 32 characters or fewer."),
        blank=False,
        null=False,
    )

    phone_number = PhoneNumberField(
        _('Phone number'),
        blank=False,
        null=False,
    )

    driver = models.ForeignKey(
        CustomUser,
        verbose_name=_('Driver'),
        related_name='crews',
        on_delete=models.CASCADE,
    )

    passengers = models.ManyToManyField(
        CustomUser,
        verbose_name=_('Passangers'),
        related_name='passenger_crews',
        blank=True,
    )

    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )

    def __str__(self) -> str:
        """Representation of a single instance."""
        return f'{self.title}-{self.id} ({self.get_status_display()}): '\
               f'{self.passengers.count()} p.'

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('logistics:crew_read', kwargs={'pk': self.pk})


class Task(GetFieldsMixin, models.Model):
    """Define a task for a SearchRequest."""
    departure = models.ForeignKey(
        Departure,
        related_name='tasks',
        verbose_name=_('Departure'),
        on_delete=models.CASCADE
    )

    title = models.CharField(
        _('Title'),
        max_length=32,
        help_text=_("Required 32 characters or fewer."),
        blank=False,
        null=False,
    )

    address = models.CharField(
        _('Address'),
        max_length=128,
        help_text=_("Required 128 characters or fewer."),
        blank=False,
        null=False,
    )

    # TODO: Coordinates from address or vice-versa
    coordinates = LocationField(
        verbose_name=_('Coordinates'),
        based_fields=['address'],
        zoom=8,
    )

    description = models.TextField(
        _('Description'),
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )

    def __str__(self) -> str:
        """Representation of a single instance."""
        return f'{self.title} ({self.coordinates.coords})'
