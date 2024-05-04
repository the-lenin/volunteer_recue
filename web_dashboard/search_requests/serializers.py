from rest_framework import serializers
from . import models


class SearchRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SearchRequest
        fields = '__all__'
