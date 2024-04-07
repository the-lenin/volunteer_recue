from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from . import models, forms, filters


# Search Request
class SerRequestBaseView(SuccessMessageMixin, View):
    """Base view for a SearchRequest."""
    model = models.SearchRequest
    fields = '__all__'
    success_url = reverse_lazy('search_requests:all')
    context_object_name = "search_requests"


class SearchRequestListView(SerRequestBaseView):
    """List all SearchRequests view."""
    template = 'search_requests/searchrequest_list.html'

    def get(self, request, *args, **kwargs):
        """Return tasks index."""
        search_requests = models.SearchRequest.objects.all()
        search_requests_filtered = filters.SearchRequestFilter(
            request.GET, queryset=search_requests, request=request
        )
        return render(
            request, self.template, {'filter': search_requests_filtered}
        )


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


# Survey
class SurveyBaseView(SuccessMessageMixin, View):
    """Base view for a Survey."""
    model = models.Survey
    context_object_name = "survey"

    def get_success_url(self):
        return reverse('search_requests:read',
                       kwargs={'pk': self.object.search_request_id})


class SurveyCreateView(SurveyBaseView, CreateView):
    """Survey create view."""
    form_class = forms.SurveyForm
    success_message = _('Survey succussfully created')

    # @overide
    def get(self, request, *args, **kwargs):
        """
        Get primary key from request and fill the search_request field with it.
        """
        search_request_pk = self.kwargs.get('pk')
        search_request = get_object_or_404(models.SearchRequest,
                                           pk=search_request_pk)
        self.initial['search_request'] = search_request
        return super().get(request, *args, **kwargs)


class SurveyDetailView(SurveyBaseView, DetailView):
    """Survey detail view."""
    fields = '__all__'


class SurveyUpdateView(SurveyBaseView, UpdateView):
    """Survey update view."""
    form_class = forms.SurveyForm
    success_message = _('Survey succussfully updated')


class SurveyDeleteView(SurveyBaseView, DeleteView):
    """Survey delete view."""
    success_message = _('Survey succussfully deleted')
