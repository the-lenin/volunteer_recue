from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from . import forms


class CustomLoginView(LoginView):
    """Assign arguments for LoginView."""
    template_name = 'auth/login.html'
    next_page = reverse_lazy('index')
    user_agreement_fp = 'templates/auth/user_agreement.md'

    form_class = forms.CustomLoginForm

    # def form_valid(self, form):
    #     remember_me = form.cleaned_data['remember_me']
    #     if not remember_me:
    #         self.request.session.set_expiry(0)
    #         self.request.session.modified = True
    #     return super().form_valid(form)

    def get_context_data(self, **kwargs):
        """Add context to super()."""
        context = super().get_context_data(**kwargs)
        with open(self.user_agreement_fp, 'r') as f:
            context['user_agreement_terms'] = f.read()
        return context
