# from django import forms
from django.forms import ModelForm
from django.forms.models import inlineformset_factory
from .import models


class TaskForm(ModelForm):
    class Meta:
        model = models.Task
        fields = '__all__'
        # widgets = {
        #     'search_request': forms.HiddenInput(),
        # }


TaskFormSet = inlineformset_factory(models.Departure, models.Task,
                                    form=TaskForm, extra=0,)
