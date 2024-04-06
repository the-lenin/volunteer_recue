from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from . import models
from django.utils.translation import gettext_lazy as _


# Search Request
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


# Survey
class SurveyBaseView(View):
    """Base view for a Survey."""
    model = models.Survey
    fields = '__all__'
    context_object_name = "survey"

    def get_success_url(self):
        """Return to detailed view of search_request."""
        return reverse('search_requests:read', self.search_requests.id)


class SurveyCreateView(SurveyBaseView, CreateView):
    """Survey create view."""
    success_message = _('Survey succussfully created')

    # @overide
    def post(self, request, *args, **kwargs):
        """Get SearchRequest primary key and assign it to Survey."""
        form = self.get_form()
        if form.is_valid():
            survey = form.save()
            search_request = models.SearchRequest.objects.get(
                pk=self.kwargs.get('pk')
            )

            if search_request:
                print(search_request.id, survey.id)
                models.SurveySearchRequest.objects.create(survey=survey,
                                                          search_request=search_request)
                return redirect(search_request.get_absolute_url())

            # TODO: Where to return if no search_request present???
            return redirect('search_requests:all')

        return self.form_invalid(form)


class SurveyDetailView(SurveyBaseView, DetailView):
    """Survey detail view."""


class SurveyUpdateView(SurveyBaseView, UpdateView):
    """Survey update view."""
    success_message = _('Survey succussfully updated')


class SurveyDeleteView(SurveyBaseView, DeleteView):
    """Survey delete view."""
    success_message = _('Survey succussfully deleted')
