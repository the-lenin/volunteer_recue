from django.views import View
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import SearchRequest


class SerRequestBaseView(View):
    """Base view for a SearchRequest."""
    model = SearchRequest
    fields = '__all__'
    success_url = reverse_lazy('search_requests:all')
    context_object_name = "search_requests"


class SearchRequestListView(SerRequestBaseView, ListView):
    """List all SearchRequests view."""


class SearchResquestCreateView(SerRequestBaseView, CreateView):
    """SearchRequest create view."""


class SearchRequestDetailView(SerRequestBaseView, DetailView):
    """SearchRequest detail view."""


class SearchRequestUpdateView(SerRequestBaseView, UpdateView):
    """SearchRequest update view."""


class SearchRequestDeleteView(SerRequestBaseView, DeleteView):
    """SearchRequest delete view."""
