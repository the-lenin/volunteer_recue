import django_filters
# from django.db.models import Q
# from django.utils.translation import gettext_lazy as _

from . import models


class CrewFilter(django_filters.FilterSet):
    """Set of filters for the Crew model."""
    # search = django_filters.CharFilter(
    #     label=_('Search'),
    #     label_suffix="",
    #     method='filter_all'
    # )

    class Meta:
        model = models.Crew
        fields = [
            # 'search',
            'status',
        ]

    # def filter_all(self, queryset, name, value):
    #     """Filter Crew queryset for multiple lookups."""
    #     if value:
    #         return queryset.filter(
    #             Q(full_name__icontains=value) |
    #             Q(city__icontains=value) |
    #             Q(phone_number__icontains=value)
    #         )

    #     return queryset


class DepartureFilter(django_filters.FilterSet):
    """Set of filters for the Departure model."""
    # search = django_filters.CharFilter(
    #     label=_('Search'),
    #     label_suffix="",
    #     method='filter_all'
    # )

    class Meta:
        model = models.Departure
        fields = [
            # 'search',
            'status',
        ]

    # def filter_all(self, queryset, name, value):
    #     """Filter Departure queryset for multiple lookups."""
    #     if value:
    #         return queryset.filter(
    #             Q(full_name__icontains=value) |
    #             Q(city__icontains=value) |
    #             Q(phone_number__icontains=value)
    #         )

    #     return queryset
