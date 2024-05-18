from django.contrib.auth.forms import UserChangeForm
from .models import CustomUser


class CustomUserChangeForm(UserChangeForm):
    """Override UserChangeForm with custom model."""
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
            'comment'
        ]
        exclude = ['password']
