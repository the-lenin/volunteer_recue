from django.views import View
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


class IndexView(View):
    """Root index view after logging."""
    @login_required
    def get(self, request, *args, **kwargs):
        return render(request, 'index.html')
