from django.db import models
from django.contrib.gis.db import models as gis_models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

PHOTOS_PATH = 'photos/'


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
        CHILD = 'CHLD', _('child')
        TEENAGER = 'TNGR', _('teenager')
        ADULT = 'ADLT', _('adult')
        OLDERLY = 'OLDR', _('olderly')

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

    # latitude = models.DecimalField(
    #     _('Latitude'),
    #     max_digits=9,
    #     decimal_places=6,
    #     blank=True,
    #     null=True,
    # )

    # longitude = models.DecimalField(
    #     _('Longitude'),
    #     max_digits=9,
    #     decimal_places=6,
    #     blank=True,
    #     null=True,
    # )

    location = gis_models.PointField(
        _('Latitutude, Longitude'),
        blank=True,
        null=True,
    )

    location_verbose = models.CharField(
        _('Nearest Location'),
        max_length=255,
        blank=True,
        null=True,
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
        upload_to=PHOTOS_PATH,
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
        return f'{self.full_name} {self.date_of_birth}, Lost@: {self.location}, Status: {self.get_status_display()}'

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


class Reporter(models.Model):
    """Class representing a person reporting missing person."""
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

    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )


class ReporterSearchRequest(models.Model):
    """
    Intermediary many-to-many model connecting Reporter to SearchRequest.
    """
    reporter = models.ForeignKey(
        Reporter,
        on_delete=models.CASCADE,
        related_name='reporter',
        verbose_name=_('Reporter'),
    )

    search_request = models.ForeignKey(
        SearchRequest,
        on_delete=models.CASCADE,
        related_name='search_request',
        verbose_name=_('Search Request'),
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

    class Meta:
        unique_together = ('reporter', 'search_request')
