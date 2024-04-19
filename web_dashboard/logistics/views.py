from django.shortcuts import render
from django.db import transaction
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from . import models, filters, forms


# class CrewBaseView(SuccessMessageMixin, View):
#     """Base view for a Crew model."""
#     model = models.Crew
#     fields = '__all__'
#     success_url = reverse_lazy('logistics:crews')
#     context_object_name = "crew"
# class CrewListView(CrewBaseView):
#     """List all Crews view."""
#     template = 'logistics/crew_list.html'
#     def get(self, request, *args, **kwargs):
#         """Return tasks index."""
#         crews = models.Crew.objects.all()
#         crews_filtered = filters.CrewFilter(
#             request.GET, queryset=crews, request=request
#         )
#         return render(
#             request, self.template, {'filter': crews_filtered}
#         )
# class CrewCreateView(CrewBaseView, CreateView):
#     """Crew create view."""
#     success_message = _('Request succussfully created')
#     def get_success_url(self):
#         """Return to the detailed view after creation."""
#         return reverse_lazy('crews:read',
#                             kwargs={'pk': self.object.pk})
# class CrewDetailView(CrewBaseView, DetailView):
#     """Crew detail view."""
# class CrewUpdateView(CrewBaseView, UpdateView):
#     """Crew update view."""
#     success_message = _('Request succussfully updated')
#     def get_success_url(self):
#         """Return to the detailed view after creation."""
#         return reverse_lazy(
#             'crews:read',
#             kwargs={'pk': self.object.pk}
#         )
# class CrewDeleteView(CrewBaseView, DeleteView):
#     """Crew delete view."""
#     success_message = _('Request succussfully deleted')


# Departure
class DepartureBaseView(SuccessMessageMixin, View):
    """Base view for a Departure model."""
    model = models.Departure
    fields = '__all__'
    success_url = reverse_lazy('logistics:all')
    context_object_name = "departure"


class DepartureListView(DepartureBaseView):
    """List all Crews view."""
    template = 'logistics/departure_list.html'

    # @overide
    def get(self, request, *args, **kwargs):
        """Return tasks index."""
        departures = models.Departure.objects.all()
        departures_filtered = filters.DepartureFilter(
            request.GET, queryset=departures, request=request
        )
        return render(
            request, self.template, {'filter': departures_filtered}
        )


class DepartureFormValidMixin:
    """Mixin with defined form_valid() method."""

    def form_valid(self, form):
        """Extend validation on TaskFormSet instances."""
        context = self.get_context_data()
        tasks = context['tasks']
        with transaction.atomic():
            # form.instance.departure = self.request.departure
            self.object = form.save()

            if tasks.is_valid():
                tasks.instance = self.object
                tasks.save()
            return super().form_valid(form)


class DepartureCreateView(DepartureFormValidMixin,
                          DepartureBaseView,
                          CreateView):
    """Departure create view."""
    success_message = _('Departure succussfully created')

    # @overide
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['tasks'] = forms.TaskFormSet(self.request.POST)
        else:
            context['tasks'] = forms.TaskFormSet()
        return context


class DepartureDetailView(DepartureBaseView, DetailView):
    """Departure detail view."""


class DepartureUpdateView(DepartureFormValidMixin,
                          DepartureBaseView,
                          UpdateView):
    """Departure update view."""
    success_message = _('Departure succussfully updated')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['tasks'] = forms.TaskFormSet(self.request.POST,
                                                 instance=self.object)
        else:
            context['tasks'] = forms.TaskFormSet(instance=self.object)
        return context


class DepartureDeleteView(DepartureBaseView, DeleteView):
    """Departure delete view."""
    success_message = _('Departure succussfully deleted')
