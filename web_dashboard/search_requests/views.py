from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from . import models
from django.utils.translation import gettext_lazy as _


class SerRequestBaseView(SuccessMessageMixin, View):
    """Base view for a SearchRequest."""
    model = models.SearchRequest
    fields = '__all__'
    success_url = reverse_lazy('search_requests:all')
    context_object_name = "search_requests"


class SearchRequestListView(SerRequestBaseView, ListView):
    """List all SearchRequests view."""


class SearchResquestCreateView(SerRequestBaseView, CreateView):
    """SearchRequest create view."""
    success_message = _('Request succussfully created')

    def get_success_url(self):
        """Return to the detailed view after creation."""
        return reverse_lazy('search_requests:read',
                            kwargs={'pk': self.object.pk})


class SearchRequestDetailView(SerRequestBaseView, DetailView):
    """SearchRequest detail view."""


class SearchRequestUpdateView(SerRequestBaseView, UpdateView):
    """SearchRequest update view."""
    success_message = _('Request succussfully updated')

    def get_success_url(self):
        """Return to the detailed view after creation."""
        return reverse_lazy(
            'search_requests:read',
            kwargs={'pk': self.object.pk}
        )


class SearchRequestDeleteView(SerRequestBaseView, DeleteView):
    """SearchRequest delete view."""
    success_message = _('Request succussfully deleted')


class SurveyBaseView(View):
    """Base view for a Survey."""
    model = models.Survey
    fields = '__all__'
    context_object_name = "survey"


class SurveyCreateView(SurveyBaseView, CreateView):
    """Survey create view."""
    success_message = _('Survey succussfully created')


class SurveyDetailView(SurveyBaseView, DetailView):
    """Survey detail view."""


class SurveyUpdateView(SurveyBaseView, UpdateView):
    """Survey update view."""
    success_message = _('Survey succussfully updated')


class SurveyDeleteView(SurveyBaseView, DeleteView):
    """Survey delete view."""
    success_message = _('Survey succussfully deleted')
