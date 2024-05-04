from rest_framework import serializers
from . import models

from web_dashboard.search_requests.serializers import SearchRequestSerializer


class DepartureSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Departure
        depth = 1
        fields = '__all__'

#    def to_representation(self, instance):
#        representation = super().to_representation(instance)
#        representation['search_request'] = SearchRequestSerializer(instance.search_request).data
##         representation['crew'] = CrewSerializer(instance.crew).data
#        return representation
