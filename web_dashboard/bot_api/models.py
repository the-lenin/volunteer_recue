from django.db import models
from django.utils.translation import gettext_lazy as _


class TelegramUser(models.Model):
    """
    Represents a Telegram User to track actions and activities of the user.
    """
    user_id = models.BigIntegerField(
        primary_key=True,
        verbose_name=_('User ID'),
    )

    last_action = models.DateTimeField(
        _('Last action'),
    )

    created_at = models.DateTimeField(
        _('Created at'),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _('Updated at'),
        auto_now=True
    )
