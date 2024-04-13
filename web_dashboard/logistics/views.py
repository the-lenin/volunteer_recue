from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from . import models, filters  # , forms


class CrewBaseView(SuccessMessageMixin, View):
    """Base view for a Crew model."""
    model = models.Crew
    fields = '__all__'
    success_url = reverse_lazy('logistics:crews')
    context_object_name = "crew"


class CrewListView(CrewBaseView):
    """List all Crews view."""
    template = 'logistics/crew_list.html'

    def get(self, request, *args, **kwargs):
        """Return tasks index."""
        crews = models.Crew.objects.all()
        crews_filtered = filters.CrewFilter(
            request.GET, queryset=crews, request=request
        )
        return render(
            request, self.template, {'filter': crews_filtered}
        )


class CrewCreateView(CrewBaseView, CreateView):
    """Crew create view."""
    success_message = _('Request succussfully created')

    def get_success_url(self):
        """Return to the detailed view after creation."""
        return reverse_lazy('crews:read',
                            kwargs={'pk': self.object.pk})


class CrewDetailView(CrewBaseView, DetailView):
    """Crew detail view."""


class CrewUpdateView(CrewBaseView, UpdateView):
    """Crew update view."""
    success_message = _('Request succussfully updated')

    def get_success_url(self):
        """Return to the detailed view after creation."""
        return reverse_lazy(
            'crews:read',
            kwargs={'pk': self.object.pk}
        )


class CrewDeleteView(CrewBaseView, DeleteView):
    """Crew delete view."""
    success_message = _('Request succussfully deleted')
