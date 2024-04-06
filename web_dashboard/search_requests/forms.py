from django import forms
from django.forms import ModelForm
from .import models


class SurveyForm(ModelForm):
    class Meta:
        model = models.Survey
        fields = '__all__'
        widgets = {
            'search_request': forms.HiddenInput(),
        }
