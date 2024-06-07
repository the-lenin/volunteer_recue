import re
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class TZOffsetHandler:
    """Handles TZ operations."""
    MIN_TZ = -720  # -12 Hrs
    MAX_TZ = 840  # +14 Hrs

    @classmethod
    def normalize_tz_offset(cls, value: str) -> int:
        match = re.match(r'([+-])(\d{2}):(\d{2})', value)
        if not match:
            raise ValueError(
                    "Invalid timezone offset format. It should be ±HH:MM"
            )
        sign, hours, minutes = match.groups()
        sign = -1 if sign == '-' else 1
        value = int(sign * (int(hours) * 60 + int(minutes)))
        if cls.MIN_TZ <= value <= cls.MAX_TZ:
            return value
        raise ValueError("Out of limits. Minimum: -12:00, Maximum: +14:00")

    @classmethod
    def represent_tz_offset(cls, value: int) -> str:
        if isinstance(value, int):
            sign = '+' if value >= 0 else '-'
            hours, minutes = divmod(abs(value), 60)
            return f'{sign}{hours:02d}:{minutes:02d}'


class TZOffsetField(forms.IntegerField):
    """Time zone field form."""
    def to_python(self, value):
        """Normalize input."""
        try:
            return TZOffsetHandler.normalize_tz_offset(value)
        except ValueError as e:
            raise forms.ValidationError(str(e))

    def prepare_value(self, value):
        """Return human readable value in string ±HH:MM."""
        try:
            return TZOffsetHandler.represent_tz_offset(value)
        except ValueError:
            return super().prepare_value(value)


class CustomUserChangeForm(UserChangeForm):
    """Override UserChangeForm with custom model."""
    timezone = TZOffsetField(
        label=_('Time zone'),
        help_text=_("Timezone offset in the format ±HH:MM"),
        widget=forms.TextInput(attrs={'placeholder': '±HH:MM'})
    )

    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = [
            'nickname',
            "first_name",
            "last_name",
            "patronymic_name",
            "email",
            "phone_number",
            'telegram_id',
            "address",
            'has_car',
            'timezone',
            'comment'
        ]
        exclude = ['password']
