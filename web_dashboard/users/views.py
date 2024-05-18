# from django.shortcuts import get_object_or_404, render
from django.views import View
# from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView,  DeleteView  # , CreateView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy  # , reverse
from django.utils.translation import gettext_lazy as _
from . import models, forms


class UserPkToKwargsMixin(View):
    """Mixin to personalize requests."""

    def dispatch(self, request, *args, **kwargs):
        """Extract user pk and add it to kwargs."""
        self.kwargs['pk'] = self.request.user.pk
        return super().dispatch(request, *args, **kwargs)


class CustomUserBaseView(SuccessMessageMixin, View):
    """Base view for a CustomUser."""
    model = models.CustomUser
    form_class = forms.CustomUserChangeForm
    success_url = reverse_lazy('index')
    context_object_name = "user"


class CustomUserUpdateView(UserPkToKwargsMixin,
                           CustomUserBaseView,
                           UpdateView):
    """CustomUser update view."""
    success_message = _('Request succussfully updated')


class CustomUserDeleteView(UserPkToKwargsMixin,
                           DeleteView):
    """SearchRequest delete view."""
    model = models.CustomUser
    success_url = reverse_lazy('index')
    success_message = _('Request succussfully deleted')
