from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from location_field.models.spatial import LocationField
from web_dashboard.custom_auth.models import CustomUser

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

    departured_at = models.DateTimeField(
        _('Departured at'),
        blank=True,
        null=True,
    )

    nickname = models.CharField(
        _('Nickname'),
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
        on_delete=models.SET_NULL
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
        return f'ID {self.id}: {self.nickname}'

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('logistics:crew_read', kwargs={'pk': self.pk})


class Task(models.Model):
    """Define a task for a SearchRequest."""
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

    coordinates = LocationField(
        _('Coordinates')
    )

    description = models.TextField(
        _('Description'),
        blank=True,
        null=True,
    )


class Departure(models.Model):
    pass
