import re
from django.contrib.auth.forms import UserChangeForm
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class TimeZoneOffsetField(forms.IntegerField):
    """Represent human readable format for TZ
    e.g.: +03:30, -05:00."""

    def to_python(self, value):
        match = re.match(r'([+-])(\d{2}):(\d{2})', value)
        if not match:
            raise forms.ValidationError(
                "Invalid timezone offset format. It should be ±HH:MM"
            )

        sign, hours, minutes = match.groups()
        sign = -1 if sign == '-' else 1
        value = int(sign * (int(hours) * 60 + int(minutes)))
        return value

    def prepare_value(self, value):
        """Return human readable value in string ±HH:MM."""
        if isinstance(value, int):
            sign = '+' if value >= 0 else '-'
            hours, minutes = divmod(abs(value), 60)
            return f'{sign}{hours:02d}:{minutes:02d}'


class CustomUserChangeForm(UserChangeForm):
    """Override UserChangeForm with custom model."""
    timezone = TimeZoneOffsetField(
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
