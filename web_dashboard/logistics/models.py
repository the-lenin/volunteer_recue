from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import Point
from phonenumber_field.modelfields import PhoneNumberField
from location_field.models.spatial import LocationField

from web_dashboard.users.models import CustomUser
from web_dashboard.search_requests import models as models_sr


class Crew(models.Model):
    """Class represent crew."""

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
        on_delete=models.CASCADE
    )

    # members = models.ManyToOneRel

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
        return f'ID {self.id} ({self.get_status_display()}): {self.title}'

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('logistics:crew_read', kwargs={'pk': self.pk})


class Task(models.Model):
    """Define a task for a SearchRequest."""
    search_request = models.ForeignKey(
        models_sr.SearchRequest,
        verbose_name=_('Search Request'),
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
        default=Point(82.919782, 55.029738),  # Novosibirsk
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


class Departure(models.Model):
    search_request = models.ForeignKey(
        models_sr.SearchRequest,
        verbose_name=_('Search Request'),
        on_delete=models.CASCADE
    )

    crew = models.OneToOneField(
        Crew,
        verbose_name=_('Crew'),
        on_delete=models.CASCADE
    )
