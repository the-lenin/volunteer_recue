from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import SearchRequest


class SearchRequestView(View):
    """Base view for a SearchRequest."""
    model = SearchRequest
    fields = '__all__'
    success_url = reverse_lazy('search_request:all')


class SearchRequestListView(SearchRequestView, ListView):
    """List all SearchRequests view."""


class SearchResquestCreateView(SearchRequestView, CreateView):
    """SearchRequest create view."""


class SearchRequestDetailView(SearchRequestView, DetailView):
    """SearchRequest detail view."""


class SearchRequestUpdateView(SearchRequestView, UpdateView):
    """SearchRequest update view."""


class SearchRequestDeleteView(SearchRequestView, DeleteView):
    """SearchRequest delete view."""
