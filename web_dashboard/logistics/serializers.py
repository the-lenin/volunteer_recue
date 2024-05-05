from rest_framework import serializers
from . import models


class DepartureSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Departure
        depth = 1
        fields = '__all__'
