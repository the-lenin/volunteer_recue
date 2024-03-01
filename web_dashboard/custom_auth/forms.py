from django.contrib.auth.forms import AuthenticationForm
from django import forms


class CustomLoginForm(AuthenticationForm):
    """Extend AuthenticationForm with 'Remember me' radio button."""
    remember_me = forms.BooleanField(required=False)
