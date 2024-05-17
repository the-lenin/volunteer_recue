from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


class CustomUser(AbstractUser):
    """
    Extend AbstractUser model with additional fields.
    """
    patronymic_name = models.CharField(
        _('Patronymic name'),
        max_length=64,
        help_text=_("Required 64 characters or fewer."),
        blank=True,
        null=True,
    )

    nickname = models.CharField(
        _('Nickname'),
        max_length=64,
        help_text=_("Required 64 characters or fewer."),
        blank=True,
        null=True,
    )

    address = models.CharField(
        _('Address'),
        max_length=255,
        help_text=_("Required 255 characters or fewer."),
    )

    phone_number = PhoneNumberField(
        _('Phone number'),
        unique=True,
        error_messages={
            "unique": _("User with such phone number already exist."),
        }
    )

    telegram_id = models.BigIntegerField(
        _('Telegram ID'),
        error_messages={
            "unique": _("User with such telegram id already exist."),
        },
        unique=True,
        blank=True,
        null=True,
    )

    has_car = models.BooleanField(
        _('Has car'),
        default=False,
    )

    comment = models.TextField(
        _('Comment'),
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

    groups = models.ManyToManyField(
        Group,
        verbose_name=_('Groups'),
        blank=True,
        related_name='custom_user_groups',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        related_name='custom_user_permissions',
        help_text=_('Specific permissions for this user.'),
    )

    REQUIRED_FIELDS = [
        'first_name',
        'last_name',
        'email',
        'phone_number',
        'address',
        'has_car',
    ]

    @property
    def full_name(self):
        """Return full name."""
        names = [self.last_name, self.first_name, self.patronymic_name]
        parts = [part for part in names if part]
        return ' '.join(parts)

    full_name.fget.short_description = _('Full name')
