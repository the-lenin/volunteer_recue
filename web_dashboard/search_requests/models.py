import os
from django.db import models
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from uuid import uuid4
from phonenumber_field.modelfields import PhoneNumberField
from location_field.models.spatial import LocationField


def path_and_rename(instance, filename):
    upload_to = 'photos'
    ext = filename.split('.')[-1]
    if instance.pk:
        filename = f'{instance.pk}.{ext}'
    else:
        filename = f'{uuid4()}.{ext}'
    return os.path.join(upload_to, filename)


class SearchRequest(models.Model):
    """
    Model representing search request of missing individual.
    """

    full_name = models.CharField(
        _('Full name'),
        max_length=128,
        help_text=_("Required 128 characters or fewer."),
        blank=False,
        null=False,
    )

    date_of_birth = models.DateField(
        _('Date of birth'),
        blank=True,
        null=True,
    )

    class AgeVerbose(models.TextChoices):
        """Choices for age categories."""
        CHILD = 'CHLD', _('Child')
        TEENAGER = 'TNGR', _('Teenager')
        ADULT = 'ADLT', _('Adult')
        OLDERLY = 'OLDR', _('Olderly')

    age = models.CharField(
        _('Age'),
        max_length=4,
        choices=AgeVerbose.choices,
        default=AgeVerbose.ADULT,
    )

    class SexVerbose(models.TextChoices):
        """Choices for gender (sex)."""
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        UNSPECIFIED = 'U', _('Unspecified')

    sex = models.CharField(
        _('Sex'),
        max_length=1,
        choices=SexVerbose.choices,
        default=SexVerbose.UNSPECIFIED,
    )

    location = LocationField(
        verbose_name=_('Location'),
        based_fields=['city'],
        zoom=8,
        default=Point(82.919782, 55.029738),  # Novosibirsk
    )

    city = models.CharField(
        _('City'),
        max_length=255,
        help_text=_('Type a city name to find coordinates on map'),
    )

    disappearance_date = models.DateField(
        _('Disappearnce Date'),
        blank=False,
        null=False,
    )

    circumstances = models.TextField(
        _('Circumstances of disapprance'),
        blank=True,
        null=True,
    )

    phone_number = PhoneNumberField(
        _('Phone number'),
        blank=True,
        null=True,
    )

    internet_data = models.TextField(
        _('Internet Data'),
        blank=True,
        null=True,
    )

    features = models.TextField(
        _('Features'),
        blank=False,
        null=False,
    )

    clothing = models.TextField(
        _('Clothing'),
        blank=False,
        null=False,
    )

    personal_belongings = models.TextField(
        _('Personal Belongings'),
        blank=False,
        null=False,
    )

    photos = models.ImageField(
        _('Photos'),
        upload_to=path_and_rename,
        blank=True,
        null=True,
    )

    health_condition = models.TextField(
        _('Health condition'),
        blank=False,
        null=False,
    )

    alcohol = models.BooleanField(
        _('Alcohol'),
        default=False,
    )

    drugs = models.BooleanField(
        _('Drugs'),
        default=False,
    )

    additional_info = models.TextField(
        _('Additional Information'),
        blank=True,
        null=True,
    )

    reporter_full_name = models.CharField(
        _('Reporter full name'),
        max_length=128,
        help_text=_("Required 128 characters or fewer."),
        blank=False,
        null=False,
    )

    reporter_contact_details = models.TextField(
        _('Reporter contact details'),
        blank=False,
        null=False,
    )

    reporter_relationship = models.CharField(
        _('Reporter relationship to missing person'),
        max_length=128,
        help_text=_("Required 128 characters or fewer."),
        blank=False,
        null=False,
    )

    reporter_has_reported_to_police = models.BooleanField(
        _('Has reporter reported to police'),
        default=False,
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
        return f'{self.full_name} {self.date_of_birth}, Lost@: {self.location}, Status: {self.get_status_display()}'  # noqa: E501

    def get_fields(self) -> list[tuple]:
        """Return list of tuples with field name and value of the instance."""
        fields = []
        for field in self._meta.fields:
            field_name = field.verbose_name
            field_value = getattr(self, field.attname)
            if field.choices:
                field_value = dict(field.choices).get(field_value)
            fields.append((field_name, field_value))
        return fields

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('search_request:read', kwargs={'pk': self.pk})


class Survey(models.Model):
    """Class representing a person surveyedi regarding missing person."""
    first_name = models.CharField(
        _('First name'),
        max_length=64,
        help_text=_("Required 64 characters or fewer."),
        blank=False,
        null=False,
    )

    last_name = models.CharField(
        _('Last name'),
        max_length=64,
        help_text=_("Required 64 characters or fewer."),
        blank=False,
        null=False,
    )

    patronymic_name = models.CharField(
        _('Patronymic name'),
        max_length=64,
        help_text=_("Required 64 characters or fewer."),
        blank=True,
        null=True,
    )

    phone_number = PhoneNumberField(
        _('Phone number'),
        blank=False,
        null=False,
    )

    relationship = models.CharField(
        _('Relationship'),
        max_length=32,
        help_text=_("Required 32 characters or fewer."),
        blank=False,
        null=False,
    )

    additiona_info = models.TextField(
        _('Additional information'),
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

    @property
    def full_name(self):
        """Return full name."""
        names = [self.last_name, self.first_name, self.patronymic_name]
        parts = [part for part in names if part]
        return ' '.join(parts)

    def __str__(self) -> str:
        """Representation of a single instance."""
        return self.full_name

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('survey:read', kwargs={'pk': self.pk})


class SurveySearchRequest(models.Model):
    """
    Intermediary many-to-many model connecting Survey to SearchRequest.
    """
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='search_requests',
        verbose_name=_('Survey'),
    )

    search_request = models.ForeignKey(
        SearchRequest,
        on_delete=models.CASCADE,
        related_name='surveys',
        verbose_name=_('Search Request'),
    )

    def __str__(self) -> str:
        """Representation of a single instance."""
        return f'{self.reporter} // {self.search_request}'
