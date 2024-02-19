from django.views import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin


class IndexView(LoginRequiredMixin, View):
    """Root index view after logging."""
    login_url = 'login'

    def get(self, request, *args, **kwargs):
        return render(request, 'index.html')
