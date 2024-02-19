from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    """Context extended."""
    template_name = 'auth/login.html'
    next_page = reverse_lazy('index')
    user_agreement_fp = 'templates/auth/user_agreement.md'

    def get_context_data(self, **kwargs):
        """Add context to super()."""
        context = super().get_context_data(**kwargs)
        with open(self.user_agreement_fp, 'r') as f:
            context['user_agreement_terms'] = f.read()
        return context
