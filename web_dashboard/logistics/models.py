from django.db import models
from django.contrib.gis.db.models import PointField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
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

    title = models.CharField(
        _('Title'),
        max_length=32,
        help_text=_("Required 32 characters or fewer."),
        blank=False,
        null=False,
    )

    class StatusVerbose(models.TextChoices):
        """Crew status choices."""
        AVAILABLE = 'A', _('Available')
        ON_MISSION = 'M', _('On mission')
        RETURNING = 'R', _('Returning')
        COMPLETED = 'C', _('Completed')

    status = models.CharField(
        _('status'),
        max_length=1,
        choices=StatusVerbose.choices,
        default=StatusVerbose.AVAILABLE,
    )

    driver = models.ForeignKey(
        CustomUser,
        verbose_name=_('Driver'),
        related_name='crews',
        on_delete=models.CASCADE,
    )

    passengers_max = models.IntegerField(
        _('Max passengers'),
        blank=False,
        null=False,
    )

    passengers = models.ManyToManyField(
        CustomUser,
        verbose_name=_('Passengers'),
        related_name='passenger_crews',
        blank=True,
    )

    pickup_location = PointField(
        _('Pickup location'),
        blank=False,
        null=False,
    )

    pickup_datetime = models.DateTimeField(
        _('Pickup at'),
        blank=False,
        null=False,
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
        return f'{self.title}-{self.id} ({self.get_status_display()})'

    def get_absolute_url(self) -> str:
        """Return absolute url to the object."""
        return reverse('logistics:crew_read', kwargs={'pk': self.pk})

    async def aaccept_join_request(self, join_request):
        """Async accept JoinRequest to crew and change it status."""
        if join_request.crew != self:
            raise ValueError("This join request does not belong to this crew.")
        if await self.passengers.acount() >= self.passengers_max:
            raise ValueError("The crew has already reached the maximum number of passengers.")  # noqa: E501

        join_request.status = JoinRequest.StatusVerbose.ACCEPTED
        await join_request.asave()
        await self.passengers.aadd(join_request.passenger)
        await self.asave()

    async def areject_join_request(self, join_request):
        """Async reject JoinRequest and change it status and remove it."""
        if join_request.crew != self:
            raise ValueError("This join request does not belong to this crew.")
        join_request.status = JoinRequest.StatusVerbose.REJECTED
        await join_request.asave()
        await self.passengers.aremove(join_request.passenger)
        await self.asave()


class JoinRequest(models.Model):
    """Model to represent join requests from passengers to crews."""
    passenger = models.ForeignKey(
        CustomUser,
        verbose_name=_('Passenger'),
        related_name='join_requests',
        on_delete=models.CASCADE,
    )

    crew = models.ForeignKey(
        Crew,
        verbose_name=_('Crew'),
        related_name='join_requests',
        on_delete=models.CASCADE,
    )

    request_time = models.DateTimeField(
        _('Request Time'),
        auto_now_add=True,
    )

    class StatusVerbose(models.TextChoices):
        """Pedestrian status choices."""
        PENDING = 'P', _('Pending')
        ACCEPTED = 'A', _('Accepted')
        REJECTED = 'R', _('Rejected')

    status = models.CharField(
        _('status'),
        max_length=1,
        choices=StatusVerbose.choices,
        default=StatusVerbose.PENDING,
    )

    class Meta:
        unique_together = ('passenger', 'crew')

    @property
    def emoji(self):
        match self.status:
            case self.StatusVerbose.PENDING:
                return "🟡"
            case self.StatusVerbose.ACCEPTED:
                return "🟢"
            case  self.StatusVerbose.REJECTED:
                return "🔴"
        return ""

    def __str__(self):
        """String representation."""
        return f'{self.passenger} ({self.get_status_display()}) -> {self.crew}'  # noqa: E501


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
