from django.forms import ModelForm
from .import models


class SearchRequestForm(ModelForm):
    class Meta:
        model = models.Task
        fields = '__all__'
#         [
#             'name',
#             'description',
#             'status',
#             'executor',
#             'labels',
#         ]
